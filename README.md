<p align="center">
  <h1 align="center">MuseLoop</h1>
  <p align="center">
    <strong>Open-source AI agent for autonomous creative multimedia pipelines</strong>
  </p>
  <p align="center">
    <a href="#quick-start">Quick Start</a> &middot;
    <a href="#how-it-works">How It Works</a> &middot;
    <a href="#skills">Skills</a> &middot;
    <a href="#configuration">Configuration</a> &middot;
    <a href="#adding-a-skill">Add a Skill</a> &middot;
    <a href="#architecture">Architecture</a>
  </p>
</p>

---

MuseLoop takes a simple creative brief — *"make a 30-second cyberpunk trailer"* — and autonomously plans, generates, critiques, and refines multimedia content through an agentic loop. It orchestrates AI models for **image, video, audio, and editing** tasks, improving output quality with each iteration.

```
Brief ──► Plan ──► Generate ──► Critique ──► Revise ──►── Done
  │                                │            │
  │                                └────────────┘
  │                              (loop until quality ≥ threshold)
  └── "Create a 30s cyberpunk trailer"
```

## Features

- **Agentic loop** — Iterative Plan → Generate → Critique → Revise cycle with configurable quality thresholds
- **5 specialized agents** — Memory, Research, Script, Director, and Critic (orchestrated via [LangGraph](https://github.com/langchain-ai/langgraph))
- **Pluggable skill system** — Image, video, audio, and editing skills with JSON manifests. Add your own in minutes
- **Multi-backend LLM** — Claude API (default), OpenAI-compatible (Ollama, vLLM, LM Studio)
- **Graceful fallbacks** — Local models → Cloud APIs → Placeholders. Always produces output
- **Git versioning** — Every iteration committed and tagged. Full rollback capability
- **Docker-ready** — CPU orchestrator + GPU ComfyUI sidecar via docker-compose

## Quick Start

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- An [Anthropic API key](https://console.anthropic.com/) for Claude
- Optional: [ffmpeg](https://ffmpeg.org/) for video/audio processing
- Optional: [ComfyUI](https://github.com/comfyanonymous/ComfyUI) for local image generation
- Optional: Docker + NVIDIA GPU for local model inference

### Install

```bash
git clone https://github.com/chalkychalk42/MuseLoop.git
cd MuseLoop

# Install dependencies
uv sync

# Configure API keys
cp .env.example .env
# Edit .env → set MUSELOOP_ANTHROPIC_API_KEY=sk-ant-xxxxx
```

### Run

```bash
# Execute a creative pipeline
uv run museloop run examples/briefs/sci_fi_trailer.json

# Dry run (plan only, no generation)
uv run museloop run examples/briefs/sci_fi_trailer.json --dry-run

# Custom settings
uv run museloop run brief.json --max-iterations 10 --threshold 0.8 --verbose

# List available skills
uv run museloop skills

# Inspect a brief without running
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
          │    ┌──────────────▼───────────────┐     │
          │    │      ResearchAgent           │     │
          │    │  Gather style keywords,      │     │
          │    │  prompt tips, references     │     │
          │    └──────────────┬───────────────┘     │
          │                   │                     │
          │    ┌──────────────▼───────────────┐     │
          │    │       ScriptAgent            │     │
          │    │  Break brief into tasks,     │     │
          │    │  write creative script       │     │
          │    └──────────────┬───────────────┘     │
          │                   │                     │
          │    ┌──────────────▼───────────────┐     │
          │    │      DirectorAgent           │     │
          │    │  Dispatch skills in parallel │     │
          │    │  ┌───────┬───────┬────────┐  │     │
          │    │  │ image │ video │ audio  │  │     │
          │    │  └───┬───┴───┬───┴────┬───┘  │     │
          │    │      └───────┼────────┘      │     │
          │    └──────────────┬───────────────┘     │
          │                   │                     │
          │    ┌──────────────▼───────────────┐     │
          │    │       CriticAgent            │     │
          │    │  Score quality (0.0 → 1.0)  │     │
          │    │  Provide revision feedback   │     │
          │    └──────────────┬───────────────┘     │
          │                   │                     │
          │         ┌─────────▼─────────┐           │
          │         │ score ≥ threshold? │           │
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

### State Machine

The loop state transitions through these phases per iteration:

```
                 ┌──────────┐
     ┌──────────►│ planning │◄──────── (start of each iteration)
     │           └────┬─────┘
     │                │  MemoryAgent + ResearchAgent + ScriptAgent
     │                ▼
     │           ┌────────────┐
     │           │ generating │ DirectorAgent dispatches skills
     │           └────┬───────┘
     │                │  Skills execute (image, video, audio, editing)
     │                ▼
     │           ┌────────────┐
     │           │ critiquing │ CriticAgent evaluates output
     │           └────┬───────┘
     │                │
     │           ┌────▼────┐
     │     NO ◄──┤  pass?  ├──► YES
     │           └─────────┘
     │                │              ┌──────────┐
     └────────────────┘              │ complete │
       (revise: next iteration)      └──────────┘
```

### Shared State

All agents communicate through a shared `LoopState` dictionary managed by LangGraph. No agent calls another directly — they read from and write to the shared state:

| Field | Type | Description |
|-------|------|-------------|
| `brief` | `dict` | The creative brief (immutable after load) |
| `iteration` | `int` | Current iteration number (1-indexed) |
| `plan` | `list[dict]` | Tasks broken down by ScriptAgent |
| `assets` | `list[dict]` | Generated assets (paths + metadata) |
| `critique` | `dict` | Score, feedback, pass/fail from CriticAgent |
| `messages` | `list` | Agent reasoning traces (LangGraph message log) |
| `memory` | `dict` | Persistent context across iterations |
| `status` | `str` | Current phase: `planning`, `generating`, `critiquing`, `complete` |

## Skills

MuseLoop ships with four built-in skills. Each skill follows a **local → API → placeholder** fallback chain:

| Skill | What It Does | Local Backend | API Fallback | Placeholder |
|-------|-------------|---------------|--------------|-------------|
| `image_gen` | Generate images | ComfyUI (Stable Diffusion) | Replicate (SDXL) | PIL colored rectangle with text |
| `video_gen` | Generate video clips | diffusers (CogVideoX) | Replicate | ffmpeg color bars with text |
| `audio_gen` | Generate music/audio | AudioCraft (MusicGen) | Replicate (MusicGen) | ffmpeg silent audio |
| `editing` | Post-processing | ffmpeg | — | — |

### Editing Operations

The `editing` skill supports these operations via ffmpeg:

| Operation | Description | Required Params |
|-----------|-------------|-----------------|
| `concat` | Concatenate multiple videos | `input_files: list[str]` |
| `overlay_audio` | Add audio track to video | `video_path`, `audio_path` |
| `trim` | Trim video/audio | `input_file`, `start`, `duration` |
| `convert` | Convert format | `input_file` |

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
MUSELOOP_QUALITY_THRESHOLD=0.7           # Score needed to accept (0.0–1.0)

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

### CLI Options

```
museloop run <brief.json> [OPTIONS]

Options:
  -o, --output-dir PATH       Output directory [default: ./output]
  -n, --max-iterations INT    Max loop iterations [default: 5]
  -t, --threshold FLOAT       Quality score to accept [default: 0.7]
  --dry-run                   Plan only, skip generation
  -v, --verbose               Enable debug logging
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
# ┌───────────┬────────────────────────┐
# │ Name      │ Description            │
# ├───────────┼────────────────────────┤
# │ my_skill  │ Does something creative│
# └───────────┴────────────────────────┘
```

Reference it in your brief's `skills_required` array, and the DirectorAgent will dispatch tasks to it.

## Architecture

### Project Structure

```
museloop/
├── src/museloop/
│   ├── cli.py                 # Typer CLI — run, skills, inspect, history, version
│   ├── config.py              # Pydantic Settings — loads .env, validates config
│   │
│   ├── core/
│   │   ├── loop.py            # Outer iteration loop (the heart of MuseLoop)
│   │   ├── state.py           # LoopState TypedDict — shared agent state
│   │   ├── graph.py           # LangGraph StateGraph — wires agents together
│   │   └── brief.py           # Brief JSON parser and validator
│   │
│   ├── agents/
│   │   ├── base.py            # BaseAgent ABC — LLM access + prompt loading
│   │   ├── memory.py          # Condenses context across iterations
│   │   ├── research.py        # Gathers style keywords and references
│   │   ├── script.py          # Breaks brief into executable plan + script
│   │   ├── director.py        # Dispatches skills in parallel
│   │   └── critic.py          # Scores output quality, decides pass/revise
│   │
│   ├── llm/
│   │   ├── base.py            # LLMBackend Protocol — swap any provider
│   │   ├── claude.py          # Anthropic Claude (async)
│   │   ├── openai_compat.py   # OpenAI-compatible (Ollama, vLLM, etc.)
│   │   └── factory.py         # get_llm_backend(config) factory
│   │
│   ├── skills/
│   │   ├── base.py            # BaseSkill ABC + SkillInput/SkillOutput
│   │   ├── registry.py        # Auto-discover skills from manifests/
│   │   ├── image_gen.py       # Stable Diffusion via ComfyUI + Replicate
│   │   ├── video_gen.py       # CogVideoX/Wan2.2 + Replicate
│   │   ├── audio_gen.py       # AudioCraft/MusicGen + Replicate
│   │   ├── editing.py         # FFmpeg post-processing
│   │   └── manifests/         # JSON manifests for each skill
│   │
│   ├── versioning/
│   │   └── git_ops.py         # Git commit + tag per iteration
│   │
│   └── utils/
│       ├── logging.py         # Structured logging (structlog)
│       ├── retry.py           # Tenacity-based retry decorator
│       └── file_io.py         # Asset path management
│
├── prompts/                   # Agent system prompts (editable .md files)
├── examples/briefs/           # Example brief JSON files
├── tests/                     # Unit + integration tests (30 tests)
├── pyproject.toml             # uv/hatch config, all dependencies
├── Dockerfile                 # CPU runtime
├── Dockerfile.gpu             # CUDA-enabled for local models
└── docker-compose.yml         # App + ComfyUI sidecar
```

### Agent Pipeline

```
┌─────────┐    ┌──────────┐    ┌────────┐    ┌──────────┐    ┌────────┐
│ Memory  │───►│ Research │───►│ Script │───►│ Director │───►│ Critic │
│  Agent  │    │  Agent   │    │ Agent  │    │  Agent   │    │ Agent  │
└─────────┘    └──────────┘    └────────┘    └──────────┘    └────────┘
     │              │               │              │              │
     ▼              ▼               ▼              ▼              ▼
  Load prior    Style tips,     Break brief    Run skills     Score 0–1,
  context &     keywords,       into tasks,    in parallel:   feedback,
  condense      references      write script   image/video/   pass or
  memory                                       audio/edit     revise
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
uv sync          # Installs all deps including dev tools
```

### Testing

```bash
uv run pytest tests/ -v              # All tests
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
