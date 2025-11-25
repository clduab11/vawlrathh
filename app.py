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

import gradio as gr
import spaces

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

        content = uploaded_file.read()
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
    if not message:
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

        history.append((message, response_text))
        yield history, ""

    except Exception as e:
        logger.exception("Chat failed")
        history.append((message, f"Error: {str(e)}"))
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
        placeholder="4 Lightning Bolt (M11) 146\\n2 Counterspell (MH2) 267",
    )
    format_dropdown = gr.Dropdown(
        choices=["Standard", "Pioneer", "Modern"],
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
        "* CSV uploads should come from the Steam Arena export.\\n"
        "* Text uploads should be the Arena clipboard format.\\n"
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

    chatbot = gr.Chatbot(label="Live Conversation", height=400)
    msg = gr.Textbox(label="Message", placeholder="Ask Vawlrathh how to fix your deck...")
    deck_context = gr.Number(label="Deck ID (optional)", precision=0)
    clear = gr.Button("Clear")

    msg.submit(chat_streaming, [msg, chatbot, deck_context], [chatbot, msg])
    clear.click(lambda: None, None, chatbot, queue=False)

def build_meta_dashboard_tab():
    """Meta dashboards tab."""
    gr.Markdown("## Meta Dashboards")
    format_dropdown = gr.Dropdown(
        choices=["Standard", "Pioneer", "Modern"],
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

    with gr.Blocks(title="Vawlrathh - Deck Analysis") as interface:
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
