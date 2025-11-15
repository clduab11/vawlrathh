# 🎥 Vawlrathh Demo Video Creation Guide

**For MCP 1st Birthday Hackathon Submission**

This guide provides step-by-step instructions for creating an AI-generated demo video (1-5 minutes) showcasing Vawlrathh's features without requiring any filming.

---

## ✅ Required Elements

Your demo video MUST show:

1. **Opening screen** with Vawlrathh intro
2. **Uploading a deck** (CSV or text)
3. **Analysis results** with mana curve visualization
4. **Chat interaction** with Vawlrathh showing consensus checking
5. **Purchase info** display with vendor pricing
6. **MCP tools panel** showing activity/invocations

**Duration:** 1-5 minutes
**Format:** 1080p MP4
**Hosting:** Vimeo (free tier) or YouTube (unlisted)

---

## 🎬 Recommended Workflow: Screen Recording + AI Voiceover

### Step 1: Record Screen Walkthrough (5-10 minutes)

**Tools (Free):**
- **iPhone:** Built-in Screen Recording (Settings → Control Center → Screen Recording)
- **Mac:** QuickTime Player (File → New Screen Recording)
- **Windows:** Xbox Game Bar (Win+G) or OBS Studio (free)
- **Linux:** SimpleScreenRecorder or OBS Studio

**What to Record:**

1. **Scene 1 - Opening (10 sec)**
   - Open Gradio interface at http://localhost:7861
   - Show Vawlrathh header with hackathon badge
   - Briefly pan across tabs

2. **Scene 2 - Upload Deck (20 sec)**
   - Navigate to "Upload Deck" tab
   - Paste demo deck into text input:
     ```
     4 Lightning Bolt (M11) 146
     4 Goblin Guide (ZEN) 126
     4 Monastery Swiftspear (KTK) 118
     4 Eidolon of the Great Revel (JOU) 93
     20 Mountain (M20) 275
     ```
   - Click "Upload Text"
   - Show success message with Deck ID

3. **Scene 3 - Analysis (30 sec)**
   - Go to "Analysis" tab
   - Click "Analyze My Deck"
   - Show loading state with personality message
   - Display full analysis results:
     - Vawlrathh's verdict
     - Mana curve visualization
     - Strengths/weaknesses
     - Meta matchups

4. **Scene 4 - Chat & Consensus (30 sec)**
   - Go to "Chat with Vawlrathh" tab
   - Show MCP tools status panel (green indicators)
   - Type: "Should I add more card draw?"
   - Send message
   - Show response with consensus badge (✓ Consensus Pass)

5. **Scene 5 - Purchase Info (20 sec)**
   - Navigate to "Purchase Info" tab
   - Click "Get Purchase Info"
   - Show total deck cost
   - Display vendor comparison table
   - Highlight per-card breakdown

6. **Scene 6 - Demo Mode (20 sec)**
   - Go to "Demo" tab
   - Click "▶ Run Demo"
   - Show progress bar and log messages
   - Display completion message

7. **Scene 7 - About/Hackathon (10 sec)**
   - Navigate to "About & Hackathon" tab
   - Show hackathon badges
   - Highlight MCP integration features
   - Display architecture diagram

**Recording Tips:**
- Use 1920x1080 resolution
- Hide desktop clutter/notifications
- Move mouse slowly and deliberately
- Pause 2-3 seconds on each important screen
- Total raw footage: ~2-3 minutes

---

### Step 2: Generate AI Voiceover (10 minutes)

**Tool: ElevenLabs** (Free trial: 10,000 characters/month)
- Sign up: https://elevenlabs.io
- Voice: Choose "Antoni" (intimidating, authoritative) or "Adam" (deep, commanding)

**Voiceover Script:**

```
I'm Vawlrathh, The Small'n. Your MTG Arena deck is probably terrible.
Let me show you how I fix it using MCP-powered analysis.

This is the Vawlrathh interface. Built for the MCP 1st Birthday Hackathon.

I can analyze decks uploaded from Steam Arena, either as CSV or text format.
Here's a Mono Red Aggro deck. Let's see how bad it is.

Upload complete. Deck ID assigned. Now let's analyze.

My analysis covers mana curve optimization, meta matchup predictions,
and strategic strengths and weaknesses. As expected, this curve needs work.

You can chat with me in real-time via WebSocket. All responses are
consensus-checked by dual AI: GPT-4 and Claude Sonnet. This prevents
hallucinations and ensures accurate advice.

Here's what makes me unique: physical card pricing. I show you exactly
what this Arena deck costs in real cardboard, from TCGPlayer, CardMarket,
and Cardhoarder. Arena-only cards are automatically excluded.

I also have a demo mode. One click loads a sample deck and runs a full
analysis workflow, showing all MCP tools in action.

Under the hood, I use nine custom MCP tools, three external MCP servers
for memory and sequential thinking, and dual AI consensus checking.
All of this is built on the Model Context Protocol.

Your deck's terrible. But now you know how to fix it.

— Vawlrathh, The Small'n. Diminutive in size, not in strategic prowess.
```

**ElevenLabs Steps:**
1. Paste script into text box
2. Select voice: "Antoni" or "Adam"
3. Adjust settings: Stability 0.6, Clarity 0.7
4. Click "Generate"
5. Download MP3 file

**Alternative Free TTS:**
- Google Cloud Text-to-Speech (Free tier: 1M chars/month)
- Play.ht (Trial: 10,000 words)
- Azure Speech Services (Trial: 5 hours)

---

### Step 3: Combine Video + Audio (15 minutes)

**Tool: CapCut** (Free, desktop or mobile)
- Download: https://www.capcut.com/

**CapCut Workflow:**

1. **Import Assets**
   - Drag screen recording into timeline
   - Drag AI voiceover MP3 into audio track

2. **Sync Audio to Video**
   - Trim video clips to match voiceover timing
   - Use "Cut" tool to remove dead space
   - Add 0.5s fade transitions between scenes

3. **Add Captions (Optional but Recommended)**
   - Click "Captions" → "Auto Captions"
   - Select English
   - CapCut will generate captions from audio
   - Review and fix any errors

4. **Add Text Overlays**
   - At 0:00: "Vawlrathh - MCP 1st Birthday Hackathon"
   - At key moments:
     - "9 Custom MCP Tools"
     - "Dual-AI Consensus (GPT-4 + Claude)"
     - "Physical Card Pricing"
     - "Sequential Reasoning"
   - Use bold, white text with black outline

5. **Add Background Music (Optional)**
   - CapCut has royalty-free music library
   - Search: "Epic" or "Tech"
   - Volume: 20% (keep voiceover primary)

6. **Export**
   - Resolution: 1080p
   - Frame rate: 30 fps
   - Format: MP4
   - Quality: High
   - File size target: < 100 MB

**Alternative Free Video Editors:**
- DaVinci Resolve (Professional, free)
- Shotcut (Open source)
- Clipchamp (Web-based, free tier)

---

### Step 4: Upload & Embed (5 minutes)

**Vimeo (Recommended):**
1. Sign up: https://vimeo.com (Free tier: 500 MB/week)
2. Click "Upload"
3. Upload your MP4
4. Title: "Vawlrathh - MCP 1st Birthday Hackathon Demo"
5. Description:
   ```
   Vawlrathh: MCP-powered MTG Arena deck analyzer
   Built for MCP's 1st Birthday Hackathon (Nov 2025)

   Features:
   - 9 custom MCP tools
   - Dual-AI consensus (GPT-4 + Claude Sonnet)
   - Physical card pricing integration
   - Real-time chat with WebSocket
   - Sequential reasoning for strategic analysis

   GitHub: https://github.com/clduab11/vawlrathh
   HF Space: https://huggingface.co/spaces/MCP-1st-Birthday/vawlrathh

   #MCPBirthday #Hackathon #MTGArena #AI #MCP
   ```
6. Privacy: "Anyone" (public)
7. Click "Save"
8. Copy embed link

**YouTube (Alternative):**
- Upload as "Unlisted" video
- Same title and description
- Tags: MCPBirthday, Hackathon, MTGArena, AI, GradioApp, MCP

**Update README:**
```markdown
- **Demo Video:** [Watch on Vimeo](https://vimeo.com/YOUR_VIDEO_ID)
```

---

## 🎨 Alternative: Fully AI-Generated Video

If you prefer not to screen record, use AI video generation:

### Tools:
1. **Google AI Studio (Veo 3)** - Free, high quality
   - https://aistudio.google.com/
   - Generate 5-10 scene descriptions
   - Example: "Dark fantasy UI showing MTG card analysis with purple and red accents"

2. **Runway Gen-3** - Free trial (125 credits)
   - https://runwayml.com/
   - Generate video clips from text prompts

3. **Luma Dream Machine** - Free tier (30 generations/month)
   - https://lumalabs.ai/dream-machine
   - Text-to-video generation

### Workflow:
1. Generate 5-7 video clips (5-10 sec each):
   - Clip 1: "Vawlrathh character intro, dark fantasy theme"
   - Clip 2: "Deck upload interface, modern UI"
   - Clip 3: "Mana curve graph animation, MTG cards"
   - Clip 4: "Chat interface with AI response, consensus badge"
   - Clip 5: "Vendor pricing table, dollar amounts highlighted"
   - Clip 6: "MCP tools diagram, purple and red tech aesthetic"
   - Clip 7: "Closing screen with GitHub and HF logos"

2. Add voiceover (ElevenLabs)
3. Assemble in CapCut
4. Add text overlays
5. Export and upload

**Pros:** No screen recording needed, more cinematic
**Cons:** Less accurate representation, more time-consuming

---

## 📊 AI Slideshow Video (Fastest Option)

### Tools:
- Canva (Free tier)
- Google Slides + voiceover

### Workflow:
1. **Take Screenshots** (10-15 images):
   - Each tab of Gradio interface
   - Key features highlighted

2. **Create Presentation:**
   - Use Canva's "Video Presentation" template
   - Or Google Slides
   - Import screenshots (1 per slide)
   - Add text overlays explaining each feature
   - Duration: 3-5 sec per slide

3. **Export as Video:**
   - Canva: "Download" → "MP4 Video"
   - Google Slides: File → Download → MP4

4. **Add Voiceover:**
   - Same ElevenLabs script as above
   - Combine in CapCut

**Pros:** Fastest method, no video editing experience needed
**Cons:** Less dynamic, static images

---

## ✅ Final Checklist

Before submitting:

- [ ] Video is 1-5 minutes long
- [ ] Shows deck upload workflow
- [ ] Demonstrates analysis with mana curve
- [ ] Shows chat with consensus checking
- [ ] Displays purchase info with vendor pricing
- [ ] MCP tools panel is visible
- [ ] Video is 1080p MP4
- [ ] Uploaded to Vimeo or YouTube
- [ ] Embed link added to README.md
- [ ] Description includes #MCPBirthday tag
- [ ] GitHub and HF Space links in description

---

## 🎯 Key Messages to Communicate

Your video should clearly demonstrate:

1. **MCP Integration** - 9 custom tools + 3 external servers
2. **Dual-AI Consensus** - GPT-4 validated by Claude Sonnet
3. **Unique Feature** - Physical card pricing (no one else has this)
4. **Real-time Chat** - WebSocket with personality
5. **Sequential Reasoning** - Step-by-step strategic analysis
6. **Polished UX** - Dark theme, Vawlrathh personality

**Tagline:** "Your deck's terrible. Let me show you how to fix it."

---

## 📞 Need Help?

- **CapCut Tutorials:** Search YouTube for "CapCut tutorial for beginners"
- **ElevenLabs Guide:** https://help.elevenlabs.io/
- **Vimeo Help:** https://vimeo.com/help

---

**Good luck with your demo video!**

— Vawlrathh, The Small'n
