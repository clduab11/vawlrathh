"""Hugging Face Space wrapper for Vawlrathh.

This module provides a pure Gradio application for deployment on Hugging Face Spaces
with ZeroGPU support. It integrates directly with Vawlrathh services instead of
using a separate FastAPI backend, ensuring compatibility with the Gradio SDK runner.

"Your deck's terrible. Let me show you how to fix it."
— Vawlrathh, The Small'n
"""

import logging
import os
import sys
import textwrap
import json
import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from dotenv import load_dotenv
import gradio as gr
import spaces

# Load environment variables from .env file
load_dotenv()

# Ensure project root is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import Services
from src.services.smart_sql import SmartSQLService
from src.services.deck_analyzer import DeckAnalyzer
from src.services.meta_intelligence import MetaIntelligenceService
from src.services.chat_agent import ConcurrentChatService
from src.services.smart_inference import SmartInferenceService
from src.services.card_market_service import CardMarketService
from src.utils.csv_parser import parse_arena_csv, parse_deck_string

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Service Initialization
# -----------------------------------------------------------------------------

# Initialize services
# Note: Async initialization happens in the event loop
sql_service = SmartSQLService()
meta_service = MetaIntelligenceService()
deck_analyzer = DeckAnalyzer(meta_service=meta_service)
chat_service = ConcurrentChatService()
inference_service = SmartInferenceService()
card_market_service = CardMarketService()

# -----------------------------------------------------------------------------
# GPU / Spaces Configuration
# -----------------------------------------------------------------------------

@spaces.GPU(duration=10)
def initialize_gpu():
    """Initialize GPU runtime for HF Spaces ZERO.

    This function exists primarily to satisfy the ZeroGPU requirement that
    at least one function must be decorated with @spaces.GPU.
    """
    import torch
    if torch.cuda.is_available():
        device = torch.cuda.get_device_name(0)
        logger.info(f"GPU initialized: {device}")
        return {"gpu": device, "cuda_available": True}
    return {"gpu": None, "cuda_available": False}

# -----------------------------------------------------------------------------
# Helper Functions (Direct Service Calls)
# -----------------------------------------------------------------------------

async def ensure_db_initialized():
    """Ensure database is initialized."""
    await sql_service.init_db()

async def handle_csv_upload(uploaded_file, previous_id):
    """Handle CSV upload by calling services directly."""
    if not uploaded_file:
        return {"status": "error", "message": "No CSV file selected"}, previous_id, previous_id

    try:
        # Ensure DB is ready
        await ensure_db_initialized()

        # Handle both file path (Gradio 4.x+) and file object (older Gradio)
        if hasattr(uploaded_file, 'read'):
            content = uploaded_file.read()
        else:
            # uploaded_file is a path string (NamedString or str)
            with open(str(uploaded_file), 'r', encoding='utf-8') as f:
                content = f.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8')

        deck = parse_arena_csv(content)
        deck_id = await sql_service.store_deck(deck)

        return {
            "status": "success",
            "message": f"Deck '{deck.name}' uploaded successfully",
            "deck_id": deck_id
        }, deck_id, deck_id
    except Exception as e:
        logger.exception("CSV upload failed")
        return {"status": "error", "message": str(e)}, previous_id, previous_id

async def handle_text_upload(deck_text, fmt, previous_id):
    """Handle text upload by calling services directly."""
    if not deck_text or not deck_text.strip():
        return {"status": "error", "message": "Deck text is empty"}, previous_id, previous_id

    try:
        # Ensure DB is ready
        await ensure_db_initialized()

        deck = parse_deck_string(deck_text)
        deck.format = fmt
        deck_id = await sql_service.store_deck(deck)

        return {
            "status": "success",
            "message": f"Deck uploaded successfully",
            "deck_id": deck_id
        }, deck_id, deck_id
    except Exception as e:
        logger.exception("Text upload failed")
        return {"status": "error", "message": str(e)}, previous_id, previous_id

async def handle_analyze(deck_id: float):
    """Analyze a deck using DeckAnalyzer."""
    if not deck_id:
        return {"status": "error", "message": "No deck ID provided"}

    try:
        deck = await sql_service.get_deck(int(deck_id))
        if not deck:
            return {"status": "error", "message": "Deck not found"}

        analysis = await deck_analyzer.analyze_deck(deck)

        # Convert to dict for JSON output
        return {
            "deck_name": analysis.deck_name,
            "overall_score": analysis.overall_score,
            "mana_curve": analysis.mana_curve.__dict__,
            "strengths": analysis.strengths,
            "weaknesses": analysis.weaknesses,
            "synergies": [s.__dict__ for s in analysis.synergies],
            "meta_matchups": [m.__dict__ for m in analysis.meta_matchups]
        }
    except Exception as e:
        logger.exception("Analysis failed")
        return {"status": "error", "message": str(e)}

async def handle_optimize(deck_id: float):
    """Generate optimization suggestions."""
    if not deck_id:
        return {"status": "error", "message": "No deck ID provided"}

    try:
        deck = await sql_service.get_deck(int(deck_id))
        if not deck:
            return {"status": "error", "message": "Deck not found"}

        analysis = await deck_analyzer.analyze_deck(deck)
        suggestions = await inference_service.generate_suggestions(deck, analysis)

        return [s.__dict__ for s in suggestions]
    except Exception as e:
        logger.exception("Optimization failed")
        return {"status": "error", "message": str(e)}

async def handle_meta_snapshot(game_format: str):
    """Fetch meta snapshot."""
    try:
        snapshot = await meta_service.get_current_meta(game_format)
        return meta_service.to_dict(snapshot)
    except Exception as e:
        logger.exception("Meta snapshot failed")
        return {"status": "error", "message": str(e)}

async def handle_memory_summary(deck_id: float):
    """Fetch deck performance history."""
    if not deck_id:
        return {"status": "error", "message": "No deck ID provided"}

    try:
        history = await sql_service.get_deck_performance(int(deck_id))
        return history
    except Exception as e:
        logger.exception("Memory summary failed")
        return {"status": "error", "message": str(e)}

async def chat_streaming(message, history, deck_id):
    """Stream chat responses using ConcurrentChatService."""
    if not message or not message.strip():
        yield history or [], ""
        return

    history = history or []

    # Prepare context
    context = {}
    if deck_id:
        try:
            deck = await sql_service.get_deck(int(deck_id))
            if deck:
                analysis = await deck_analyzer.analyze_deck(deck)
                context = {
                    "deck": {"name": deck.name, "format": deck.format},
                    "analysis": {"overall_score": analysis.overall_score}
                }
        except Exception as e:
            logger.error(f"Failed to load deck context: {e}")

    # Call chat service
    # Note: ConcurrentChatService isn't a generator yet, so we await the full response
    # In a future update, we could make it stream
    try:
        result = await chat_service.chat(message, context)
        response_text = result["response"]

        if result.get("consensus_checked") and not result.get("consensus_passed"):
            response_text += f"\n\n⚠️ **Consensus Warning**: {result.get('consensus_breaker', {}).get('reason')}"

        # Gradio 5.0.0 requires messages as dictionaries with 'role' and 'content' keys
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response_text})
        yield history, ""

    except Exception as e:
        logger.exception("Chat failed")
        # Gradio 5.0.0 requires messages as dictionaries with 'role' and 'content' keys
        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": f"Error: {str(e)}"})
        yield history, ""

# -----------------------------------------------------------------------------
# UI Builders
# -----------------------------------------------------------------------------

REPO_URL = "https://github.com/clduab11/vawlrathh"
HACKATHON_URL = "https://huggingface.co/MCP-1st-Birthday"
HF_DEPLOYMENT_GUIDE_URL = f"{REPO_URL}/blob/main/docs/HF_DEPLOYMENT.md"

def build_gpu_status_tab():
    """GPU status and initialization tab."""
    gr.Markdown("## GPU Status")

    gpu_status = gr.JSON(label="GPU Information", value={})
    init_btn = gr.Button("Initialize GPU", variant="primary")

    init_btn.click(
        fn=initialize_gpu,
        outputs=gpu_status
    )

    gr.Markdown(
        "Click 'Initialize GPU' to test GPU availability. "
        "This is optional - the app works on CPU if GPU is not available."
    )

def build_deck_uploader_tab():
    """Deck uploader tab."""
    gr.Markdown("## Deck Uploads")
    deck_id_state = gr.State(value=None)
    deck_id_box = gr.Number(label="Latest Deck ID", interactive=False)
    upload_status = gr.JSON(label="Upload Response", value={})

    with gr.Row():
        csv_input = gr.File(file_types=[".csv"], label="Arena CSV Export")
        upload_btn = gr.Button("Upload CSV", variant="primary")

    upload_btn.click(
        fn=handle_csv_upload,
        inputs=[csv_input, deck_id_state],
        outputs=[upload_status, deck_id_state, deck_id_box],
    )

    gr.Markdown("### Arena Text Export")
    deck_text_input = gr.Textbox(
        lines=10,
        label="Arena Export",
        placeholder="4 Lightning Bolt (M11) 146\n2 Counterspell (MH2) 267",
    )
    format_dropdown = gr.Dropdown(
        choices=["Standard", "Pioneer", "Modern", "Alchemy", "Historic", "Explorer", "Timeless", "Brawl", "Historic Brawl", "Limited (Draft)", "Limited (Sealed)"],
        value="Standard",
        label="Format",
    )
    text_upload_btn = gr.Button("Upload Text", variant="secondary")

    text_upload_btn.click(
        fn=handle_text_upload,
        inputs=[deck_text_input, format_dropdown, deck_id_state],
        outputs=[upload_status, deck_id_state, deck_id_box],
    )

    gr.Markdown("### Tips")
    gr.Markdown(
        "* CSV uploads should come from the Steam Arena export.\n"
        "* Text uploads should be the Arena clipboard format.\n"
        "* The latest `deck_id` works across the Meta dashboard and chat tabs."
    )

def build_analysis_tab():
    """Deck analysis and optimization tab."""
    gr.Markdown("## Deck Analysis & Optimization")

    deck_id_input = gr.Number(label="Deck ID", precision=0)

    with gr.Row():
        analyze_btn = gr.Button("Analyze Deck", variant="primary")
        optimize_btn = gr.Button("Get Suggestions", variant="secondary")

    analysis_json = gr.JSON(label="Analysis Results")
    suggestions_json = gr.JSON(label="Optimization Suggestions")

    analyze_btn.click(
        fn=handle_analyze,
        inputs=deck_id_input,
        outputs=analysis_json
    )

    optimize_btn.click(
        fn=handle_optimize,
        inputs=deck_id_input,
        outputs=suggestions_json
    )

def build_chat_ui_tab():
    """Chat interface using Gradio Chatbot."""
    gr.Markdown("## Chat with Vawlrathh")
    gr.Markdown("Ask me about your deck, mulligan decisions, sideboard strategies, or meta matchups.")

    chatbot = gr.Chatbot(
        label="Live Conversation",
        height=400,
    )
    with gr.Row():
        msg = gr.Textbox(
            label="Message",
            placeholder="Ask Vawlrathh how to fix your deck...",
            scale=4,
            container=False,
        )
        submit_btn = gr.Button("Send", variant="primary", scale=1)

    with gr.Row():
        deck_context = gr.Number(label="Deck ID (optional)", precision=0, scale=2)
        clear = gr.Button("Clear Chat", variant="secondary", scale=1)

    # Wire up submit events
    msg.submit(
        fn=chat_streaming,
        inputs=[msg, chatbot, deck_context],
        outputs=[chatbot, msg],
    )
    submit_btn.click(
        fn=chat_streaming,
        inputs=[msg, chatbot, deck_context],
        outputs=[chatbot, msg],
    )
    clear.click(fn=lambda: ([], ""), inputs=None, outputs=[chatbot, msg], queue=False)

def build_meta_dashboard_tab():
    """Meta dashboards tab."""
    gr.Markdown("## Meta Dashboards")
    format_dropdown = gr.Dropdown(
        choices=["Standard", "Pioneer", "Modern", "Alchemy", "Historic", "Explorer", "Timeless", "Brawl", "Historic Brawl", "Limited (Draft)", "Limited (Sealed)"],
        value="Standard",
        label="Format",
    )
    meta_btn = gr.Button("Load Meta Snapshot", variant="primary")
    meta_json = gr.JSON(label="Meta Intelligence", value={})

    meta_btn.click(
        fn=handle_meta_snapshot,
        inputs=format_dropdown,
        outputs=meta_json,
    )

    deck_input = gr.Number(label="Deck ID", precision=0)
    memory_btn = gr.Button("Load Smart Memory", variant="secondary")
    memory_json = gr.JSON(label="Memory Summary", value={})

    memory_btn.click(
        fn=handle_memory_summary,
        inputs=deck_input,
        outputs=memory_json,
    )

def check_environment():
    """Check required environment variables and return HTML summary."""
    env_status = {}
    required_keys = {
        "OPENAI_API_KEY": "Required for AI-powered deck analysis and chat",
        "ANTHROPIC_API_KEY": "Required for consensus checking",
    }
    optional_keys = {
        "HF_TOKEN": "Used for CLI-based syncs and GitHub workflow dispatch",
        "TAVILY_API_KEY": "Recommended for meta intelligence",
        "EXA_API_KEY": "Recommended for semantic search",
    }

    has_missing_required = False

    for key, description in required_keys.items():
        if os.getenv(key):
            env_status[key] = "✓ Configured"
        else:
            env_status[key] = f"✗ Missing - {description}"
            has_missing_required = True

    for key, description in optional_keys.items():
        if os.getenv(key):
            env_status[key] = "✓ Configured"
        else:
            env_status[key] = f"⚠ Not configured - {description}"

    status_html = "<h3>Environment Configuration</h3><ul>"
    for key, status in env_status.items():
        status_html += f"<li><strong>{key}:</strong> {status}</li>"
    status_html += "</ul>"

    if has_missing_required:
        status_html += (
            "<p style='color: red;'><strong>⚠ Warning:</strong> "
            "Some required API keys are missing. Configure them in the HF Space settings."
            "</p>"
        )

    return status_html

def create_gradio_interface():
    """Create the main Gradio interface."""

    # About content
    about_html = textwrap.dedent(
        f"""
<div style="padding: 20px;">
    <h1>Vawlrathh</h1>
    <p style="font-style: italic; color: #666;">
        "Your deck's terrible. Let me show you how to fix it."<br/>
        — <strong>Vawlrathh, The Small'n</strong>
    </p>

    <h2>🎯 What This Is</h2>
    <p>
        Listen up. I'm <strong>Vawlrathh, The Small'n</strong>—a pint-sized,
        sharp-tongued version of Volrath, The Fallen. Despite my stature, I
        know MTG Arena better than you know your own deck (which, frankly,
        isn't saying much).
    </p>

    <p>
        <strong>Vawlrathh</strong> is an MCP-powered deck analysis tool
        that actually works. It analyzes your janky brews, tells you what's
        wrong (plenty), and helps you build something that won't embarrass
        you at FNM.
    </p>

    <h3>What Makes This Not-Garbage</h3>
    <ul>
        <li><strong>Real-Time Strategy Chat:</strong> Talk to me directly.
        I'll tell you the truth</li>
        <li><strong>AI Consensus Checking:</strong> Two AI brains so you don't
        get bad advice</li>
        <li><strong>Sequential Reasoning:</strong> Breaks down complex
        decisions into steps you can follow</li>
        <li><strong>Full MCP Integration:</strong> Memory, sequential thinking,
        omnisearch—the works</li>
    </ul>

    <h2>📖 How to Use</h2>
    
    <h3>Uploading Decks</h3>
    <ol>
        <li><strong>Export from Arena:</strong> In MTG Arena, go to your deck and click "Export" to copy to clipboard</li>
        <li><strong>Paste in Deck Uploads tab:</strong> Go to the "Deck Uploads" tab and paste your deck list in the text area</li>
        <li><strong>Or upload CSV:</strong> If you have a CSV export from Steam Arena, upload it directly</li>
        <li><strong>Select format:</strong> Choose your format (Standard, Pioneer, Modern, etc.) and click "Upload"</li>
        <li><strong>Note the Deck ID:</strong> After upload, you'll receive a Deck ID to use in other tabs</li>
    </ol>

    <h3>Using Chat</h3>
    <ol>
        <li><strong>Go to Chat tab:</strong> Navigate to the "Chat" tab</li>
        <li><strong>Enter Deck ID (optional):</strong> If you want deck-specific advice, enter your Deck ID</li>
        <li><strong>Ask anything:</strong> Ask for deck analysis, mulligan advice, sideboard strategies, or meta matchup tips</li>
        <li><strong>Example questions:</strong>
            <ul>
                <li>"What are my deck's weaknesses?"</li>
                <li>"Should I mulligan a hand with 2 lands and 5 spells?"</li>
                <li>"How do I sideboard against control?"</li>
                <li>"What cards should I cut to improve consistency?"</li>
            </ul>
        </li>
    </ol>

    <h3>Navigating Tabs</h3>
    <ul>
        <li><strong>Deck Uploads:</strong> Upload your deck via CSV or text paste</li>
        <li><strong>Analysis:</strong> Get detailed deck analysis including mana curve, strengths, weaknesses, and synergies. Enter your Deck ID and click "Analyze Deck" for full breakdown, or "Get Suggestions" for optimization recommendations</li>
        <li><strong>Chat:</strong> Have a conversation with Vawlrathh about strategy, mulligan decisions, and deck improvements</li>
        <li><strong>Meta Intelligence:</strong> View current meta snapshots for your format and track deck performance history</li>
        <li><strong>Status:</strong> Check API key configuration status</li>
        <li><strong>GPU Status:</strong> Test GPU availability (optional - app works on CPU)</li>
    </ul>

    <h3>🎖️ MCP 1st Birthday Hackathon</h3>
    <p>
        This project is submitted for the
        <strong>MCP 1st Birthday Hackathon</strong>. Visit the
        <a href="https://huggingface.co/MCP-1st-Birthday" target="_blank">
            hackathon page
        </a>
        to see more MCP-powered projects.
    </p>

    <p style="margin-top: 30px; color: #666;">
        <strong>Repository:</strong>
        <a href="{REPO_URL}" target="_blank">
            github.com/clduab11/vawlrathh
        </a>
    </p>
 </div>
        """
    )

    env_status_html = check_environment()

    # ==========================================================================
    # VAWLRATHH THEME SYSTEM v2.0
    # Comprehensive CSS with Safari/WebKit compatibility and light/dark themes
    # ==========================================================================
    
    custom_css = """
/* ==========================================================================
   VAWLRATHH THEME SYSTEM v2.0
   
   TABLE OF CONTENTS:
   1. CSS Custom Properties (Variables)
      1.1 Base Tokens (Theme-Independent)
      1.2 Dark Theme (Default)
      1.3 Light Theme
   2. Reset & Base Styles
   3. Typography (with Safari-safe gradients)
   4. Components
      4.1 Buttons
      4.2 Inputs
      4.3 Cards/Panels (with backdrop-filter fallbacks)
      4.4 Tabs
      4.5 Chat Interface
      4.6 JSON Display
   5. Gradio Overrides
   6. Media Queries
      6.1 Theme Switching (System Preference)
      6.2 Responsive Design
      6.3 Accessibility (Reduced Motion, High Contrast)
   ========================================================================== */

/* --------------------------------------------------------------------------
   1. CSS CUSTOM PROPERTIES
   -------------------------------------------------------------------------- */

/* 1.1 Base Tokens (Theme-Independent) */
:root {
  /* Brand Colors */
  --color-brand-purple: #a855f7;
  --color-brand-purple-light: #c084fc;
  --color-brand-purple-dark: #9333ea;
  --color-brand-blue: #3b82f6;
  --color-brand-blue-light: #60a5fa;
  --color-brand-blue-dark: #2563eb;
  
  /* Gradients */
  --gradient-brand: linear-gradient(135deg, var(--color-brand-purple) 0%, var(--color-brand-blue) 100%);
  --gradient-brand-subtle: linear-gradient(135deg, var(--color-brand-purple-dark) 0%, var(--color-brand-blue-dark) 100%);
  
  /* Spacing System */
  --spacing-xs: 0.25rem;
  --spacing-sm: 0.5rem;
  --spacing-md: 1rem;
  --spacing-lg: 1.5rem;
  --spacing-xl: 2rem;
  --spacing-2xl: 3rem;
  
  /* Border Radius */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-xl: 16px;
  --radius-full: 9999px;
  
  /* Typography */
  --font-family-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --font-family-mono: 'Fira Code', 'SF Mono', 'Consolas', monospace;
  
  --font-size-xs: 0.75rem;
  --font-size-sm: 0.875rem;
  --font-size-md: 1rem;
  --font-size-lg: 1.125rem;
  --font-size-xl: 1.25rem;
  --font-size-2xl: 1.5rem;
  --font-size-3xl: 2rem;
  --font-size-4xl: 2.5rem;
  
  --font-weight-normal: 400;
  --font-weight-medium: 500;
  --font-weight-semibold: 600;
  --font-weight-bold: 700;
  --font-weight-extrabold: 800;
  
  --line-height-tight: 1.25;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.75;
  
  /* Transitions */
  --transition-fast: 150ms ease;
  --transition-normal: 250ms ease;
  --transition-slow: 350ms ease;
  
  /* Z-Index Scale */
  --z-dropdown: 100;
  --z-modal: 200;
  --z-tooltip: 300;
  --z-toast: 400;
}

/* 1.2 Dark Theme (Default) */
:root,
[data-theme="dark"] {
  /* Background Colors */
  --color-bg-primary: #0f0f1a;
  --color-bg-secondary: #1a1a2e;
  --color-bg-tertiary: #252542;
  
  /* Surface Colors */
  --color-surface-default: rgba(30, 30, 46, 0.95);
  --color-surface-hover: rgba(37, 37, 66, 0.95);
  --color-surface-active: rgba(45, 45, 80, 0.95);
  
  /* Text Colors - WCAG AAA Compliant */
  --color-text-primary: #f1f5f9;
  --color-text-secondary: #cbd5e1;
  --color-text-tertiary: #94a3b8;
  --color-text-inverse: #0f0f1a;
  
  /* Border Colors */
  --color-border-default: rgba(148, 163, 184, 0.2);
  --color-border-subtle: rgba(148, 163, 184, 0.1);
  --color-border-strong: rgba(148, 163, 184, 0.4);
  --color-border-accent: rgba(168, 85, 247, 0.4);
  --color-border-focus: var(--color-brand-purple);
  
  /* Accent Colors */
  --color-accent-primary: var(--color-brand-purple);
  --color-accent-primary-hover: var(--color-brand-purple-light);
  --color-accent-primary-active: var(--color-brand-purple-dark);
  --color-accent-secondary: var(--color-brand-blue);
  --color-accent-secondary-hover: var(--color-brand-blue-light);
  --color-accent-secondary-active: var(--color-brand-blue-dark);
  
  /* Input Colors - Improved Contrast */
  --color-input-bg: rgba(37, 37, 66, 0.8);
  --color-input-bg-hover: rgba(45, 45, 80, 0.8);
  --color-input-bg-focus: rgba(45, 45, 80, 0.95);
  --color-input-border: rgba(148, 163, 184, 0.3);
  --color-input-border-hover: rgba(148, 163, 184, 0.5);
  --color-input-border-focus: var(--color-brand-purple);
  --color-input-text: #f1f5f9;
  --color-input-placeholder: #64748b;
  
  /* Semantic Colors */
  --color-success: #22c55e;
  --color-success-bg: rgba(34, 197, 94, 0.15);
  --color-success-border: rgba(34, 197, 94, 0.4);
  --color-warning: #f59e0b;
  --color-warning-bg: rgba(245, 158, 11, 0.15);
  --color-warning-border: rgba(245, 158, 11, 0.4);
  --color-error: #ef4444;
  --color-error-bg: rgba(239, 68, 68, 0.15);
  --color-error-border: rgba(239, 68, 68, 0.4);
  --color-info: #3b82f6;
  --color-info-bg: rgba(59, 130, 246, 0.15);
  --color-info-border: rgba(59, 130, 246, 0.4);
  
  /* Shadows */
  --shadow-color: rgba(0, 0, 0, 0.5);
  --shadow-sm: 0 1px 2px var(--shadow-color);
  --shadow-md: 0 4px 12px var(--shadow-color);
  --shadow-lg: 0 8px 24px var(--shadow-color);
  --shadow-xl: 0 12px 48px var(--shadow-color);
  --shadow-glow-purple: 0 0 20px rgba(168, 85, 247, 0.3);
  --shadow-glow-blue: 0 0 20px rgba(59, 130, 246, 0.3);
}

/* 1.3 Light Theme (Designed from Scratch - NOT inverted dark) */
[data-theme="light"] {
  /* Background Colors - Cool gray palette */
  --color-bg-primary: #fafbfc;
  --color-bg-secondary: #ffffff;
  --color-bg-tertiary: #f1f5f9;
  
  /* Surface Colors */
  --color-surface-default: rgba(255, 255, 255, 0.95);
  --color-surface-hover: rgba(241, 245, 249, 0.95);
  --color-surface-active: rgba(226, 232, 240, 0.95);
  
  /* Text Colors - WCAG AAA Compliant */
  --color-text-primary: #0f172a;
  --color-text-secondary: #334155;
  --color-text-tertiary: #64748b;
  --color-text-inverse: #ffffff;
  
  /* Border Colors */
  --color-border-default: rgba(15, 23, 42, 0.12);
  --color-border-subtle: rgba(15, 23, 42, 0.06);
  --color-border-strong: rgba(15, 23, 42, 0.2);
  --color-border-accent: rgba(168, 85, 247, 0.3);
  --color-border-focus: var(--color-brand-purple);
  
  /* Accent Colors - Darker for light bg contrast */
  --color-accent-primary: #9333ea;
  --color-accent-primary-hover: #a855f7;
  --color-accent-primary-active: #7e22ce;
  --color-accent-secondary: #2563eb;
  --color-accent-secondary-hover: #3b82f6;
  --color-accent-secondary-active: #1d4ed8;
  
  /* Input Colors */
  --color-input-bg: #ffffff;
  --color-input-bg-hover: #f8fafc;
  --color-input-bg-focus: #ffffff;
  --color-input-border: rgba(15, 23, 42, 0.2);
  --color-input-border-hover: rgba(15, 23, 42, 0.3);
  --color-input-border-focus: var(--color-brand-purple);
  --color-input-text: #0f172a;
  --color-input-placeholder: #94a3b8;
  
  /* Semantic Colors - Adjusted for light bg */
  --color-success: #16a34a;
  --color-success-bg: rgba(22, 163, 74, 0.1);
  --color-success-border: rgba(22, 163, 74, 0.3);
  --color-warning: #d97706;
  --color-warning-bg: rgba(217, 119, 6, 0.1);
  --color-warning-border: rgba(217, 119, 6, 0.3);
  --color-error: #dc2626;
  --color-error-bg: rgba(220, 38, 38, 0.1);
  --color-error-border: rgba(220, 38, 38, 0.3);
  --color-info: #2563eb;
  --color-info-bg: rgba(37, 99, 235, 0.1);
  --color-info-border: rgba(37, 99, 235, 0.3);
  
  /* Shadows - Lighter for light theme */
  --shadow-color: rgba(15, 23, 42, 0.08);
  --shadow-sm: 0 1px 2px var(--shadow-color);
  --shadow-md: 0 4px 12px var(--shadow-color);
  --shadow-lg: 0 8px 24px var(--shadow-color);
  --shadow-xl: 0 12px 48px var(--shadow-color);
  --shadow-glow-purple: 0 0 20px rgba(147, 51, 234, 0.2);
  --shadow-glow-blue: 0 0 20px rgba(37, 99, 235, 0.2);
}

/* --------------------------------------------------------------------------
   2. RESET & BASE STYLES
   -------------------------------------------------------------------------- */

*, *::before, *::after {
  box-sizing: border-box;
}

/* --------------------------------------------------------------------------
   3. TYPOGRAPHY (with Safari-safe gradients)
   -------------------------------------------------------------------------- */

.gradio-container {
  /* Fallback for older browsers */
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-family: var(--font-family-sans);
  /* Fallback color */
  color: #f1f5f9;
  color: var(--color-text-primary);
  line-height: 1.5;
  line-height: var(--line-height-normal);
}

/* Header H1 - Safari-safe gradient text with solid fallback */
.gradio-container h1 {
  /* CRITICAL: Solid color fallback - ALWAYS visible on Safari/M1 */
  color: #a855f7;
  color: var(--color-brand-purple);
  font-weight: 800;
  font-weight: var(--font-weight-extrabold);
  text-align: center;
  font-size: 2.5rem;
  font-size: var(--font-size-4xl);
  margin-bottom: var(--spacing-sm);
  /* M1 GPU optimization - force compositing layer */
  transform: translateZ(0);
  -webkit-transform: translateZ(0);
}

/* Progressive enhancement: Only apply gradient if fully supported */
@supports (-webkit-background-clip: text) and (-webkit-text-fill-color: transparent) {
  .gradio-container h1 {
    background: linear-gradient(90deg, #a855f7 0%, #3b82f6 100%);
    background: var(--gradient-brand);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
  }
}

/* Subtitle styling */
.gradio-container h1 + .markdown {
  text-align: center;
  color: #94a3b8;
  color: var(--color-text-tertiary);
  font-style: italic;
  margin-bottom: var(--spacing-xl);
}

/* --------------------------------------------------------------------------
   4. COMPONENTS
   -------------------------------------------------------------------------- */

/* 4.1 Buttons - Primary */
.gr-button-primary {
  /* Fallback background */
  background: #a855f7;
  background: var(--gradient-brand);
  border: none;
  /* Fallback color */
  color: #0f0f1a;
  color: var(--color-text-inverse);
  font-weight: 600;
  font-weight: var(--font-weight-semibold);
  border-radius: 8px;
  border-radius: var(--radius-md);
  padding: var(--spacing-sm) var(--spacing-lg);
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
  box-shadow: var(--shadow-md), var(--shadow-glow-purple);
  /* M1 GPU optimization */
  transform: translateZ(0);
  -webkit-transform: translateZ(0);
}

.gr-button-primary:hover {
  transform: translateY(-2px) translateZ(0);
  box-shadow: var(--shadow-lg), var(--shadow-glow-purple);
}

/* 4.1 Buttons - Secondary */
.gr-button-secondary {
  background: rgba(59, 130, 246, 0.2);
  background: var(--color-info-bg);
  border: 1px solid rgba(59, 130, 246, 0.4);
  border: 1px solid var(--color-info-border);
  color: #60a5fa;
  color: var(--color-accent-secondary-hover);
  font-weight: 600;
  font-weight: var(--font-weight-semibold);
  border-radius: 8px;
  border-radius: var(--radius-md);
  transition: background var(--transition-fast), border-color var(--transition-fast);
}

.gr-button-secondary:hover {
  background: rgba(59, 130, 246, 0.3);
  border-color: var(--color-accent-secondary);
}

/* 4.2 Inputs */
input, textarea, select {
  /* Fallback background */
  background: rgba(37, 37, 66, 0.8);
  background: var(--color-input-bg);
  border: 1px solid rgba(148, 163, 184, 0.3);
  border: 1px solid var(--color-input-border);
  border-radius: 8px;
  border-radius: var(--radius-md);
  color: #f1f5f9;
  color: var(--color-input-text);
  padding: var(--spacing-sm) var(--spacing-md);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
  -webkit-appearance: none;
  appearance: none;
}

input:hover, textarea:hover, select:hover {
  background: var(--color-input-bg-hover);
  border-color: var(--color-input-border-hover);
}

input:focus, textarea:focus, select:focus {
  outline: none;
  background: var(--color-input-bg-focus);
  border-color: var(--color-input-border-focus);
  box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.15);
}

input::placeholder, textarea::placeholder {
  color: #64748b;
  color: var(--color-input-placeholder);
}

/* Focus-visible for keyboard navigation */
:focus-visible {
  outline: 2px solid var(--color-brand-purple);
  outline-offset: 2px;
}

:focus:not(:focus-visible) {
  outline: none;
}

/* 4.3 Cards/Panels - Safe Glassmorphism with 3-tier fallback */

/* Tier 1: Solid background fallback - works everywhere */
.gr-box, .gr-form, .gr-panel {
  /* Solid fallback - guaranteed to work */
  background: rgba(30, 30, 46, 0.95);
  background: var(--color-surface-default);
  border: 1px solid rgba(168, 85, 247, 0.15);
  border: 1px solid var(--color-border-accent);
  border-radius: 16px;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
}

/* Tier 2: Blur supported - lighter bg with blur effect */
@supports (backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px)) {
  .gr-box, .gr-form, .gr-panel {
    background: rgba(30, 30, 46, 0.8);
    -webkit-backdrop-filter: blur(12px);
    backdrop-filter: blur(12px);
  }
}

/* Light theme panels */
[data-theme="light"] .gr-box,
[data-theme="light"] .gr-form,
[data-theme="light"] .gr-panel {
  background: var(--color-surface-default);
  border-color: var(--color-border-default);
}

@supports (backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px)) {
  [data-theme="light"] .gr-box,
  [data-theme="light"] .gr-form,
  [data-theme="light"] .gr-panel {
    background: rgba(255, 255, 255, 0.8);
    -webkit-backdrop-filter: blur(12px);
    backdrop-filter: blur(12px);
  }
}

/* 4.4 Tabs */
.tab-nav {
  /* Solid fallback */
  background: rgba(30, 30, 46, 0.95);
  background: var(--color-surface-default);
  border-radius: 12px;
  border-radius: var(--radius-lg);
  padding: var(--spacing-sm);
  border: 1px solid var(--color-border-accent);
}

@supports (backdrop-filter: blur(1px)) or (-webkit-backdrop-filter: blur(1px)) {
  .tab-nav {
    background: rgba(30, 30, 46, 0.6);
    -webkit-backdrop-filter: blur(10px);
    backdrop-filter: blur(10px);
  }
}

button.selected {
  background: var(--gradient-brand);
  color: var(--color-text-inverse);
  border-radius: var(--radius-md);
  font-weight: var(--font-weight-semibold);
}

/* 4.5 Chat Interface */
.message-row {
  margin: var(--spacing-md) 0;
}

.message.user {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  background: linear-gradient(135deg, var(--color-brand-blue) 0%, var(--color-brand-blue-dark) 100%);
  border-radius: var(--radius-xl) var(--radius-xl) var(--radius-sm) var(--radius-xl);
  padding: var(--spacing-md) var(--spacing-lg);
  color: white;
  color: var(--color-text-inverse);
  box-shadow: var(--shadow-md);
  /* Light theme text override */
  --color-text-inverse: #ffffff;
}

.message.bot {
  background: linear-gradient(135deg, #a855f7 0%, #9333ea 100%);
  background: linear-gradient(135deg, var(--color-brand-purple) 0%, var(--color-brand-purple-dark) 100%);
  border-radius: var(--radius-xl) var(--radius-xl) var(--radius-xl) var(--radius-sm);
  padding: var(--spacing-md) var(--spacing-lg);
  color: white;
  color: var(--color-text-inverse);
  box-shadow: var(--shadow-md);
  /* Light theme text override */
  --color-text-inverse: #ffffff;
}

/* 4.6 JSON Display */
.json-holder {
  background: #252542;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-lg);
  padding: var(--spacing-md);
  font-family: var(--font-family-mono);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

/* --------------------------------------------------------------------------
   5. GRADIO OVERRIDES (Minimal !important - only where Gradio requires)
   -------------------------------------------------------------------------- */

/* Main container background - Gradio sets inline styles requiring !important */
.gradio-container {
  /* Fallback */
  background: linear-gradient(135deg, #0f0f1a 0%, #1a1a2e 50%, #252542 100%);
  background: linear-gradient(135deg,
    var(--color-bg-primary) 0%,
    var(--color-bg-secondary) 50%,
    var(--color-bg-tertiary) 100%
  ) !important;
}

/* Light theme container */
[data-theme="light"] .gradio-container,
.gradio-container[data-theme="light"] {
  background: linear-gradient(135deg,
    var(--color-bg-primary) 0%,
    var(--color-bg-secondary) 50%,
    var(--color-bg-tertiary) 100%
  ) !important;
}

/* Labels - Gradio sets inline color styles */
label {
  color: #cbd5e1;
  color: var(--color-text-secondary) !important;
  font-weight: var(--font-weight-semibold);
  margin-bottom: var(--spacing-sm);
}

/* Links - Gradio default link styles need override */
a {
  color: #60a5fa;
  color: var(--color-accent-secondary-hover);
  text-decoration: none;
  transition: color var(--transition-fast);
}

a:hover {
  color: var(--color-accent-primary);
}

/* Footer */
footer {
  background: rgba(15, 23, 42, 0.4);
  border-top: 1px solid var(--color-border-subtle);
  padding: var(--spacing-md);
  margin-top: var(--spacing-xl);
}

/* --------------------------------------------------------------------------
   6. MEDIA QUERIES
   -------------------------------------------------------------------------- */

/* 6.1 Theme Switching - System Preference */
@media (prefers-color-scheme: light) {
  :root:not([data-theme="dark"]) {
    /* Light theme variable overrides for system preference */
    --color-bg-primary: #fafbfc;
    --color-bg-secondary: #ffffff;
    --color-bg-tertiary: #f1f5f9;
    --color-surface-default: rgba(255, 255, 255, 0.95);
    --color-surface-hover: rgba(241, 245, 249, 0.95);
    --color-surface-active: rgba(226, 232, 240, 0.95);
    --color-text-primary: #0f172a;
    --color-text-secondary: #334155;
    --color-text-tertiary: #64748b;
    --color-text-inverse: #ffffff;
    --color-border-default: rgba(15, 23, 42, 0.12);
    --color-border-subtle: rgba(15, 23, 42, 0.06);
    --color-border-strong: rgba(15, 23, 42, 0.2);
    --color-input-bg: #ffffff;
    --color-input-bg-hover: #f8fafc;
    --color-input-bg-focus: #ffffff;
    --color-input-border: rgba(15, 23, 42, 0.2);
    --color-input-border-hover: rgba(15, 23, 42, 0.3);
    --color-input-text: #0f172a;
    --color-input-placeholder: #94a3b8;
    --shadow-color: rgba(15, 23, 42, 0.08);
  }
}

/* 6.2 Responsive Design */
@media (max-width: 768px) {
  .gradio-container h1 {
    font-size: var(--font-size-2xl);
  }
  
  .gr-box, .gr-form, .gr-panel {
    border-radius: var(--radius-md);
  }
}

/* 6.3 Accessibility */

/* Reduced Motion - Disable animations */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  
  .gr-button-primary:hover {
    transform: none;
  }
  
  /* Disable backdrop-filter for reduced motion */
  .gr-box, .gr-form, .gr-panel, .tab-nav {
    -webkit-backdrop-filter: none;
    backdrop-filter: none;
    background: var(--color-surface-default);
  }
}

/* High Contrast Mode */
@media (prefers-contrast: more) {
  :root {
    --color-border-default: rgba(148, 163, 184, 0.5);
    --color-border-strong: rgba(148, 163, 184, 0.8);
    --color-input-border: rgba(148, 163, 184, 0.6);
  }
}

/* Windows High Contrast Mode */
@media (forced-colors: active) {
  .gr-button-primary {
    border: 2px solid ButtonText;
    background: ButtonFace;
    color: ButtonText;
  }
  
  .gr-button-primary:hover {
    background: Highlight;
    color: HighlightText;
  }
  
  input, textarea, select {
    border: 2px solid ButtonText;
  }
  
  input:focus, textarea:focus, select:focus {
    outline: 3px solid Highlight;
  }
}
"""

    # Theme Controller JavaScript for persistence
    theme_js = """
<script>
/**
 * ThemeController for Vawlrathh
 * Manages theme switching with system preference respect and localStorage persistence
 */
const ThemeController = {
  STORAGE_KEY: 'vawlrathh-theme',
  
  init() {
    // Load saved preference or use system default
    const saved = localStorage.getItem(this.STORAGE_KEY);
    if (saved && (saved === 'dark' || saved === 'light')) {
      this.applyTheme(saved);
    }
    // If no saved preference, CSS handles system preference via media query
    
    // Listen for system preference changes
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        // Only respond to system changes if no manual override
        if (!localStorage.getItem(this.STORAGE_KEY)) {
          this.applyTheme(e.matches ? 'dark' : 'light');
        }
      });
    }
  },
  
  applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    // Dispatch event for any listeners
    window.dispatchEvent(new CustomEvent('themechange', { detail: { theme } }));
  },
  
  toggle() {
    const current = document.documentElement.getAttribute('data-theme');
    const systemPrefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const effectiveCurrent = current || (systemPrefersDark ? 'dark' : 'light');
    const next = effectiveCurrent === 'dark' ? 'light' : 'dark';
    
    this.applyTheme(next);
    localStorage.setItem(this.STORAGE_KEY, next);
  },
  
  setTheme(theme) {
    if (theme === 'system') {
      localStorage.removeItem(this.STORAGE_KEY);
      document.documentElement.removeAttribute('data-theme');
    } else {
      this.applyTheme(theme);
      localStorage.setItem(this.STORAGE_KEY, theme);
    }
  }
};

// Initialize on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => ThemeController.init());
} else {
  ThemeController.init();
}

// Expose globally for Gradio button integration
window.themeController = ThemeController;
</script>
"""

    # Inject custom CSS and Theme Controller via gr.HTML for maximum compatibility
    with gr.Blocks(title="Vawlrathh - Deck Analysis") as interface:
        # CSS injection must be first element to apply styles to all subsequent components
        gr.HTML(f"<style>{custom_css}</style>")
        # Theme controller JavaScript for persistence
        gr.HTML(theme_js)
        gr.Markdown("# Vawlrathh, The Small'n")
        gr.Markdown("*Your deck's terrible. Let me show you how to fix it.*")

        with gr.Tabs():
            with gr.Tab("About"):
                gr.HTML(about_html)

            with gr.Tab("Deck Uploads"):
                build_deck_uploader_tab()

            with gr.Tab("Analysis"):
                build_analysis_tab()

            with gr.Tab("Chat"):
                build_chat_ui_tab()

            with gr.Tab("Meta Intelligence"):
                build_meta_dashboard_tab()

            with gr.Tab("Status"):
                gr.HTML(env_status_html)

            with gr.Tab("GPU Status"):
                build_gpu_status_tab()

        footer_md = textwrap.dedent(
            f"""
            ---
            <p style="text-align: center; color: #666; font-size: 0.9em;">
                Diminutive in size, not in strategic prowess. |
                <a href="{REPO_URL}" target="_blank">
                    GitHub Repository
                </a>
                |
                <a href="{HACKATHON_URL}" target="_blank">
                    MCP 1st Birthday Hackathon
                </a>
            </p>
            """
        )
        gr.Markdown(footer_md)

    return interface

# Create the Gradio app
demo = create_gradio_interface()

# Launch logic not needed for HF Spaces, as it imports 'demo' directly
# via the sdk: gradio configuration.
if __name__ == "__main__":
    demo.launch()
