<p align="center">
  <h1 align="center">MuseLoop</h1>
  <p align="center">
    <strong>Open-source AI agent for autonomous creative multimedia pipelines</strong>
  </p>
  <p align="center">
    <a href="#memecoin-content-kit">Memecoin Kit</a> &middot;
    <a href="#quick-start">Quick Start</a> &middot;
    <a href="#templates">Templates</a> &middot;
    <a href="#skills">Skills</a> &middot;
    <a href="#mcp-server">MCP Server</a> &middot;
    <a href="#web-dashboard">Dashboard</a> &middot;
    <a href="#export-pipeline">Export</a> &middot;
    <a href="#architecture">Architecture</a>
  </p>
</p>

---

MuseLoop takes a simple creative brief — *"make a 30-second cyberpunk trailer"* — and autonomously plans, generates, critiques, and refines multimedia content through an agentic loop. It orchestrates AI models for **image, video, audio, and editing** tasks, improving output quality with each iteration.

Ship content for **TikTok, YouTube Shorts, Twitter/X, Dexscreener, pump.fun, Telegram, Discord** — all from a single command.

```
Brief ──► Plan ──► Generate ──► Critique ──► Revise ──►── Done
  │                                │            │
  │                                └────────────┘
  │                              (loop until quality >= threshold)
  └── "Create a 30s cyberpunk trailer"
```

## Features

- **Agentic loop** — Iterative Plan > Generate > Critique > Revise cycle with configurable quality thresholds
- **5 specialized agents** — Memory, Research, Script, Director, and Critic (orchestrated via [LangGraph](https://github.com/langchain-ai/langgraph))
- **9 pluggable skills** — Image gen (FLUX/SD), video gen, audio gen, editing, img2img, TTS, upscaling, captions. Add your own in minutes
- **Memecoin content kit** — One command generates logos, Dexscreener banners, pump.fun assets, Twitter content, Telegram stickers, Discord banners, promo thumbnails
- **10 workflow templates** — TikTok, YouTube Shorts, trailers, brand videos, music videos, social carousels, and 3 memecoin-specific templates
- **17 export presets** — Platform-specific output for YouTube, Instagram, TikTok, Twitter, Dexscreener, pump.fun, Telegram, Discord
- **Claude Vision** — CriticAgent evaluates generated images/video frames visually for quality scoring
- **MCP server** — Plug MuseLoop directly into Claude Desktop or Claude Code as an MCP tool
- **Web dashboard** — Real-time pipeline monitoring with Alpine.js SPA and WebSocket updates
- **Rich TUI** — Live terminal progress display with agent spinners, score panels, and asset galleries
- **Multi-backend LLM** — Claude API (default), OpenAI-compatible (Ollama, vLLM, LM Studio)
- **Conditional graph routing** — Smart iteration skipping (research cache, director retries, human-in-the-loop approval)
- **Graceful fallbacks** — Local models > Cloud APIs > Placeholders. Always produces output
- **Git versioning** — Every iteration committed and tagged. Full rollback capability
- **Docker-ready** — CPU orchestrator + GPU ComfyUI sidecar via docker-compose
- **210 tests** — Comprehensive unit and integration test coverage

## Memecoin Content Kit

Generate a complete memecoin content package with a single command. Logos, banners, social media assets, memes — everything a token launch needs.

```bash
# Full content kit for a new token
museloop memecoin "DogWifHat" "WIF" --concept "A dog wearing a hat" --vibe degen

# Specific assets only
museloop memecoin "PepeCoin" "PEPE" --vibe retro --chain ETH --assets token_logo,dexscreener_banner,twitter_header

# Generate brief only (inspect before running)
museloop memecoin "MoonCat" "MCAT" --concept "Cats on the moon" --brief-only

# Custom vibe and tagline
museloop memecoin "BasedFrog" "BFROG" --vibe neon --chain BASE --tagline "The most based frog on Base"
```

### What Gets Generated

| Asset | Dimensions | Use Case |
|-------|-----------|----------|
| `token_logo` | 1024x1024 | Token logo for listings, wallets, aggregators |
| `dexscreener_banner` | 1500x500 | Dexscreener pair page banner |
| `pumpfun_banner` | 800x200 | pump.fun token page header |
| `twitter_header` | 1500x500 | Twitter/X profile banner |
| `twitter_profile` | 400x400 | Twitter/X profile picture |
| `twitter_post_announcement` | 1200x675 | Launch announcement graphic |
| `twitter_post_meme` | 1200x675 | Community meme content |
| `telegram_sticker` | 512x512 | Telegram sticker pack asset |
| `discord_banner` | 960x540 | Discord server banner |
| `promo_video_thumbnail` | 1920x1080 | YouTube/social video thumbnail |

### Vibes

Choose an aesthetic for your token's content:

| Vibe | Style |
|------|-------|
| `degen` | Crypto-native, green candles, diamond hands, ape energy |
| `cute` | Kawaii, soft colors, wholesome, community-first |
| `dark` | Edgy, mysterious, shadowy, underground |
| `neon` | Cyberpunk, glowing, synthwave, high contrast |
| `retro` | Pixel art, 8-bit, nostalgic, old internet |

### Memecoin Templates

Three specialized workflow templates for crypto content:

```bash
# Full launch kit — logo, banners, social, stickers, video thumbnail
museloop run "Launch my memecoin" --template memecoin_launch

# Social media content factory — Twitter threads, memes, engagement graphics
museloop run "Create viral social content" --template memecoin_social

# Hype video — animated logo reveal, promo reel, TikTok/Twitter clip
museloop run "Make a hype video" --template memecoin_video
```

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- An [Anthropic API key](https://console.anthropic.com/) for Claude
- Optional: [ffmpeg](https://ffmpeg.org/) for video/audio/export processing
- Optional: [ComfyUI](https://github.com/comfyanonymous/ComfyUI) for local image generation
- Optional: Docker + NVIDIA GPU for local model inference

### Install

```bash
git clone https://github.com/chalkychalk42/MuseLoop.git
cd MuseLoop

# Install core dependencies
uv sync

# Install with optional features
uv sync --extra mcp        # MCP server for Claude Desktop/Code
uv sync --extra web        # Web dashboard
uv sync --extra templates  # YAML workflow templates
uv sync --all-extras       # Everything

# Configure API keys
cp .env.example .env
# Edit .env -> set MUSELOOP_ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### Run

```bash
# Execute a creative pipeline
uv run museloop run examples/briefs/sci_fi_trailer.json

# Use a template
uv run museloop run "Create a TikTok dance video" --template tiktok_vertical

# Memecoin content kit
uv run museloop memecoin "DogWifHat" "WIF" --concept "A dog wearing a hat" --vibe degen

# Dry run (plan only, no generation)
uv run museloop run examples/briefs/sci_fi_trailer.json --dry-run

# Rich TUI mode with live progress
uv run museloop run brief.json --max-iterations 10 --threshold 0.8 --verbose

# List skills, templates, export presets
uv run museloop skills
uv run museloop templates
uv run museloop export --list

# Inspect a brief
uv run museloop inspect examples/briefs/brand_video.json

# View iteration history
uv run museloop history
```

### Docker

```bash
# Build and run with ComfyUI sidecar (requires NVIDIA GPU)
docker compose up

# CPU-only (uses API fallbacks for generation)
docker build -t museloop .
docker run --env-file .env -v ./output:/app/output museloop run examples/briefs/sci_fi_trailer.json
```

## MCP Server

Run MuseLoop as an MCP server for direct integration with Claude Desktop or Claude Code.

```bash
# Start the MCP server
uv run museloop serve
```

### Claude Desktop Configuration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "museloop": {
      "command": "uv",
      "args": ["--directory", "/path/to/MuseLoop", "run", "museloop", "serve"],
      "env": {
        "MUSELOOP_ANTHROPIC_API_KEY": "sk-ant-xxxxx"
      }
    }
  }
}
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `museloop_run` | Start a full pipeline from inline brief parameters |
| `museloop_generate_image` | Generate a single image (returns ImageContent) |
| `museloop_generate_audio` | Generate audio/music |
| `museloop_skills` | List available generation skills |
| `museloop_jobs` | List running/completed jobs |
| `museloop_status` | Check job progress |
| `museloop_approve` | Resolve human-in-the-loop approval gate |

## Web Dashboard

Real-time pipeline monitoring with a browser-based UI.

```bash
# Launch the dashboard
uv run museloop dashboard

# Custom host/port
uv run museloop dashboard --host 0.0.0.0 --port 9000
```

Features:
- Job list with status indicators
- Real-time WebSocket progress updates
- Asset gallery with inline previews
- Iteration timeline with scores
- Human-in-the-loop approval button
- Dark theme

## Templates

MuseLoop ships with 10 workflow templates that preconfigure skills, export settings, and step sequences.

```bash
# List all templates
uv run museloop templates

# Inspect a template
uv run museloop templates trailer

# Use a template
uv run museloop run "My creative task" --template tiktok_vertical
```

| Template | Category | Aspect Ratio | Description |
|----------|----------|-------------|-------------|
| `tiktok_vertical` | social | 9:16 | TikTok vertical video |
| `youtube_shorts` | social | 9:16 | YouTube Shorts |
| `trailer` | cinematic | 16:9 | Movie/game trailer |
| `brand_video` | marketing | 16:9 | Brand promotional video |
| `podcast_visual` | audio | 16:9 | Podcast visualizer |
| `music_video` | music | 16:9 | Music video |
| `social_carousel` | social | 1:1 | Multi-image carousel |
| `memecoin_launch` | crypto | mixed | Full token launch kit |
| `memecoin_social` | crypto | 16:9 | Social media content factory |
| `memecoin_video` | crypto | 9:16 | Hype video / promo reel |

## Skills

MuseLoop ships with 9 built-in skills. Each generation skill follows a **local > API > placeholder** fallback chain:

| Skill | What It Does | Local Backend | API Fallback | Placeholder |
|-------|-------------|---------------|--------------|-------------|
| `image_gen` | Generate images | ComfyUI (Stable Diffusion) | Replicate (SDXL) | PIL colored rectangle |
| `flux_gen` | FLUX image generation | diffusers (FLUX) | Replicate (FLUX Pro) | PIL placeholder |
| `video_gen` | Generate video clips | diffusers (CogVideoX) | Replicate | ffmpeg color bars |
| `audio_gen` | Generate music/audio | AudioCraft (MusicGen) | Replicate (MusicGen) | ffmpeg silent audio |
| `editing` | Post-processing | ffmpeg | -- | -- |
| `img2img` | Image-to-image / style transfer | ComfyUI img2img | Replicate | PIL filter |
| `tts` | Text-to-speech | Bark / Tortoise | Replicate | ffmpeg silent audio |
| `upscale` | Image upscaling | Real-ESRGAN | Replicate | PIL Lanczos resize |
| `captions` | Subtitles / captions | Whisper + ffmpeg | Replicate Whisper | SRT stub |

### Editing Operations

The `editing` skill supports these operations via ffmpeg:

| Operation | Description | Required Params |
|-----------|-------------|-----------------|
| `concat` | Concatenate multiple videos | `input_files: list[str]` |
| `overlay_audio` | Add audio track to video | `video_path`, `audio_path` |
| `trim` | Trim video/audio | `input_file`, `start`, `duration` |
| `convert` | Convert format | `input_file` |

## Export Pipeline

Export generated content to platform-specific formats with a single command.

```bash
# Export to Instagram Reels format
uv run museloop export video.mp4 --preset instagram_reels

# List all available presets
uv run museloop export --list

# Custom output path and resize mode
uv run museloop export image.png --preset dexscreener_banner --output banner.png --mode fill
```

### Export Presets

| Preset | Resolution | Aspect Ratio | Use Case |
|--------|-----------|-------------|----------|
| `youtube_1080p` | 1920x1080 | 16:9 | YouTube standard |
| `youtube_4k` | 3840x2160 | 16:9 | YouTube 4K |
| `instagram_reels` | 1080x1920 | 9:16 | Instagram Reels |
| `instagram_square` | 1080x1080 | 1:1 | Instagram posts |
| `tiktok` | 1080x1920 | 9:16 | TikTok |
| `twitter` | 1280x720 | 16:9 | Twitter/X video |
| `dexscreener_banner` | 1500x500 | 3:1 | Dexscreener pair banner |
| `dexscreener_icon` | 256x256 | 1:1 | Dexscreener token icon |
| `pumpfun_banner` | 800x200 | 4:1 | pump.fun header |
| `pumpfun_icon` | 400x400 | 1:1 | pump.fun token icon |
| `twitter_header` | 1500x500 | 3:1 | Twitter/X profile banner |
| `twitter_post` | 1200x675 | 16:9 | Twitter/X post image |
| `twitter_profile` | 400x400 | 1:1 | Twitter/X profile picture |
| `telegram_sticker` | 512x512 | 1:1 | Telegram sticker |
| `discord_banner` | 960x540 | 16:9 | Discord server banner |
| `token_logo_sm` | 128x128 | 1:1 | Small token logo |
| `token_logo_lg` | 1024x1024 | 1:1 | Large token logo |

## How It Works

### The Agentic Loop

MuseLoop runs an iterative refinement loop. Each iteration passes through five specialized agents, and the loop continues until the **CriticAgent** scores the output above the quality threshold (default: 0.7) or `max_iterations` is reached.

```
                    ┌─────────────────────┐
                    │    Load Brief       │
                    │  (parse JSON input) │
                    └──────────┬──────────┘
                               │
                ┌──────────────▼──────────────┐
                │      ITERATION  N           │
                │  (up to max_iterations)     │
                └──────────────┬──────────────┘
                               │
          ┌────────────────────▼────────────────────┐
          │                                         │
          │          LangGraph  StateGraph           │
          │                                         │
          │    ┌──────────────────────────────┐     │
          │    │       MemoryAgent            │     │
          │    │  Load/condense context from  │     │
          │    │  prior iterations            │     │
          │    └──────────────┬───────────────┘     │
          │                   │                     │
          │         ┌─────────▼─────────┐           │
          │         │  skip research?   │           │
          │         └────┬─────────┬────┘           │
          │           NO │      YES│                │
          │    ┌─────────▼───┐     │                │
          │    │ Research    │     │                │
          │    │ Agent       │     │                │
          │    └─────────┬───┘     │                │
          │              └────┬────┘                │
          │                   │                     │
          │    ┌──────────────▼───────────────┐     │
          │    │       ScriptAgent            │     │
          │    │  Break brief into tasks,     │     │
          │    │  write creative script       │     │
          │    └──────────────┬───────────────┘     │
          │                   │                     │
          │    ┌──────────────▼───────────────┐     │
          │    │      DirectorAgent           │     │
          │    │  Dispatch skills in parallel  │     │
          │    │  ┌───────┬───────┬────────┐  │     │
          │    │  │ image │ video │ audio  │  │     │
          │    │  └───┬───┴───┬───┴────┬───┘  │     │
          │    │      └───────┼────────┘      │     │
          │    └──────────────┬───────────────┘     │
          │                   │                     │
          │         ┌─────────▼─────────┐           │
          │         │  retry director?  │           │
          │         └────┬─────────┬────┘           │
          │           NO │      YES│                │
          │              │  (0 assets, 1 retry)     │
          │              │                          │
          │    ┌─────────▼────────────────┐         │
          │    │       CriticAgent            │     │
          │    │  Score quality (0.0 -> 1.0)  │     │
          │    │  (with Claude Vision)        │     │
          │    └──────────────┬───────────────┘     │
          │                   │                     │
          │         ┌─────────▼─────────┐           │
          │         │ score >= threshold?│           │
          │         └────┬─────────┬────┘           │
          │           YES│         │NO              │
          └──────────────┼─────────┼────────────────┘
                         │         │
                         │    ┌────▼────┐
                         │    │ Revise  │──── back to ITERATION N+1
                         │    └─────────┘
                    ┌────▼────┐
                    │  Done   │
                    │ Output  │
                    └─────────┘
```

### Conditional Routing

The graph uses conditional edges for smart routing:

- **Research skip** — On iteration > 1, if style keywords are already cached, skip straight to ScriptAgent
- **Director retry** — If DirectorAgent produces zero assets, retry once before sending to CriticAgent
- **Human-in-the-loop** — Optional approval gate for borderline scores (enable with `human_in_loop: true` in config)

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# REQUIRED — Anthropic API key for Claude
MUSELOOP_ANTHROPIC_API_KEY=sk-ant-xxxxx

# LLM settings
MUSELOOP_LLM_BACKEND=claude              # "claude" or "openai"
MUSELOOP_CLAUDE_MODEL=claude-sonnet-4-20250514

# Loop settings
MUSELOOP_MAX_ITERATIONS=5                # Max refinement iterations
MUSELOOP_QUALITY_THRESHOLD=0.7           # Score needed to accept (0.0-1.0)

# Paths
MUSELOOP_OUTPUT_DIR=./output
MUSELOOP_PROMPTS_DIR=./prompts

# Optional — ComfyUI for local image/video generation
MUSELOOP_COMFYUI_URL=http://localhost:8188

# Optional — Replicate for cloud generation fallback
MUSELOOP_REPLICATE_API_KEY=r8_xxxxx

# Optional — OpenAI-compatible (for Ollama/local models)
MUSELOOP_OPENAI_BASE_URL=http://localhost:11434/v1
```

### CLI Commands

```
museloop run <brief> [OPTIONS]         Execute a creative pipeline
museloop memecoin <name> <ticker>      Generate memecoin content kit
museloop skills [name]                 List or inspect skills
museloop templates [name]              List or inspect templates
museloop export <file> --preset <p>    Export to platform format
museloop inspect <brief.json>          Parse and show brief contents
museloop history                       Show git iteration history
museloop serve                         Start MCP server
museloop dashboard                     Launch web dashboard
museloop version                       Show version
```

### Brief Format

Briefs are JSON files that describe the creative task:

```json
{
    "task": "Create a 30-second sci-fi movie trailer",
    "style": "cyberpunk",
    "duration_seconds": 30,
    "skills_required": ["image_gen", "video_gen", "audio_gen", "editing"],
    "constraints": {
        "aspect_ratio": "16:9",
        "resolution": "1920x1080",
        "tone": "dark, atmospheric, neon-lit"
    },
    "reference_assets": []
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `task` | Yes | What to create — the creative prompt |
| `style` | No | Visual/creative style keywords |
| `duration_seconds` | No | Target duration for video/audio output |
| `skills_required` | No | Which skills to use (auto-detected if empty) |
| `constraints` | No | Additional constraints (aspect ratio, resolution, tone, etc.) |
| `reference_assets` | No | Paths to reference files for style guidance |

## Adding a Skill

Adding a new skill takes two files: a Python class and a JSON manifest.

### 1. Create the Skill Class

Create `src/museloop/skills/my_skill.py`:

```python
from museloop.skills.base import BaseSkill, SkillInput, SkillOutput
from pathlib import Path

class MySkill(BaseSkill):
    name = "my_skill"
    description = "Does something creative"

    async def execute(self, input: SkillInput, config: dict) -> SkillOutput:
        output_path = config.get("output_path", "output.png")

        # Your generation logic here
        # input.prompt  — the generation prompt
        # input.params  — additional parameters dict

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        # ... generate and save to output_path ...

        return SkillOutput(
            success=True,
            asset_paths=[output_path],
            metadata={"source": "my_skill"},
        )
```

### 2. Create the Manifest

Create `src/museloop/skills/manifests/my_skill.json`:

```json
{
    "name": "my_skill",
    "description": "Does something creative",
    "module": "museloop.skills.my_skill",
    "class": "MySkill",
    "inputs": {
        "prompt": "string"
    },
    "outputs": {
        "output_path": "string"
    },
    "requires_gpu": false,
    "fallback": null
}
```

### 3. Done

The skill registry auto-discovers it on next run:

```bash
uv run museloop skills
```

Reference it in your brief's `skills_required` array, and the DirectorAgent will dispatch tasks to it.

## Architecture

### Project Structure

```
museloop/
├── src/museloop/
│   ├── cli.py                 # Typer CLI — 10 commands
│   ├── config.py              # Pydantic Settings — loads .env, validates config
│   │
│   ├── core/
│   │   ├── loop.py            # Outer iteration loop with event callbacks
│   │   ├── state.py           # LoopState TypedDict — shared agent state
│   │   ├── graph.py           # LangGraph StateGraph — conditional routing
│   │   └── brief.py           # Brief JSON parser and validator
│   │
│   ├── agents/
│   │   ├── base.py            # BaseAgent ABC — LLM + vision support
│   │   ├── memory.py          # Condenses context across iterations
│   │   ├── research.py        # Gathers style keywords and references
│   │   ├── script.py          # Breaks brief into executable plan + script
│   │   ├── director.py        # Dispatches skills in parallel
│   │   └── critic.py          # Scores quality with Claude Vision
│   │
│   ├── llm/
│   │   ├── base.py            # LLMBackend Protocol + vision methods
│   │   ├── claude.py          # Anthropic Claude (async + multimodal)
│   │   ├── openai_compat.py   # OpenAI-compatible (Ollama, vLLM, etc.)
│   │   └── factory.py         # get_llm_backend(config) factory
│   │
│   ├── skills/                # 9 pluggable generation skills
│   │   ├── base.py            # BaseSkill ABC + SkillInput/SkillOutput
│   │   ├── registry.py        # Auto-discover skills from manifests/
│   │   ├── image_gen.py       # ComfyUI + Replicate + PIL fallback
│   │   ├── flux_gen.py        # FLUX via diffusers + Replicate
│   │   ├── video_gen.py       # CogVideoX + Replicate
│   │   ├── audio_gen.py       # AudioCraft/MusicGen + Replicate
│   │   ├── editing.py         # FFmpeg post-processing
│   │   ├── img2img.py         # Image-to-image / style transfer
│   │   ├── tts.py             # Text-to-speech (Bark/Tortoise)
│   │   ├── upscale.py         # Real-ESRGAN + PIL Lanczos
│   │   ├── captions.py        # Whisper + ffmpeg subtitle burn-in
│   │   └── manifests/         # JSON manifests for each skill
│   │
│   ├── templates/             # Workflow template system
│   │   ├── base.py            # WorkflowTemplate + ExportSettings models
│   │   ├── registry.py        # YAML template discovery
│   │   └── builtin/           # 10 YAML templates
│   │
│   ├── export/                # Platform export pipeline
│   │   ├── presets.py         # 17 export presets (video + crypto platforms)
│   │   └── renderer.py        # ffmpeg resize/crop/letterbox/encode
│   │
│   ├── memecoin/              # Memecoin content generator
│   │   └── generator.py       # TokenMeta, ASSET_SPECS, brief generation
│   │
│   ├── mcp/                   # MCP server for Claude Desktop/Code
│   │   ├── server.py          # FastMCP server (stdio transport)
│   │   ├── handlers.py        # Tool handler implementations
│   │   └── job_state.py       # Job lifecycle tracking
│   │
│   ├── web/                   # Web dashboard
│   │   ├── app.py             # FastAPI application factory
│   │   ├── routes.py          # REST API endpoints
│   │   ├── ws.py              # WebSocket real-time events
│   │   ├── models.py          # Pydantic request/response models
│   │   ├── job_manager.py     # Job lifecycle management
│   │   └── static/            # Alpine.js SPA (no build step)
│   │
│   ├── ui/                    # Rich TUI for terminal
│   │   └── progress.py        # Live progress display with Rich
│   │
│   ├── versioning/
│   │   └── git_ops.py         # Git commit + tag per iteration
│   │
│   └── utils/
│       ├── logging.py         # Structured logging (structlog)
│       ├── retry.py           # Tenacity-based retry decorator
│       ├── file_io.py         # Asset path management
│       └── vision.py          # Image extraction + resize for Claude Vision
│
├── prompts/                   # Agent system prompts (editable .md files)
├── examples/briefs/           # Example brief JSON files
├── tests/                     # 210 tests (unit + integration)
├── pyproject.toml             # uv/hatch config, all dependencies
├── Dockerfile                 # CPU runtime
├── Dockerfile.gpu             # CUDA-enabled for local models
└── docker-compose.yml         # App + ComfyUI sidecar
```

### Skill Fallback Chain

Each generation skill follows this pattern:

```
┌───────────────┐     ┌──────────────┐     ┌─────────────┐
│  Local Model  │────►│   Cloud API  │────►│ Placeholder │
│  (ComfyUI/    │fail │  (Replicate) │fail │  (PIL/ffmpeg │
│   diffusers)  │     │              │     │   fallback)  │
└───────────────┘     └──────────────┘     └─────────────┘
```

This ensures MuseLoop **always produces output**, even without GPU hardware or API keys — placeholders are generated so the pipeline completes and the CriticAgent can still provide structural feedback.

## Development

### Setup

```bash
git clone https://github.com/chalkychalk42/MuseLoop.git
cd MuseLoop
uv sync --all-extras    # Installs all deps including dev tools
```

### Testing

```bash
uv run pytest tests/ -v              # All 210 tests
uv run pytest tests/unit/ -v         # Unit tests only
uv run pytest tests/integration/ -v  # Integration tests only
uv run pytest tests/ --cov=museloop  # With coverage
```

### Linting & Formatting

```bash
uv run ruff check src/ tests/       # Lint
uv run ruff format src/ tests/       # Format
uv run mypy src/                     # Type check
```

### Makefile Shortcuts

```bash
make setup        # uv sync
make test         # Run all tests
make lint         # Ruff lint
make format       # Ruff format
make typecheck    # Mypy
make docker-build # Build Docker images
make clean        # Remove build artifacts
```

## License

MIT
