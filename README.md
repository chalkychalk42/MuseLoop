<p align="center">
  <h1 align="center">MuseLoop</h1>
  <p align="center">
    <strong>AI-powered media factory. One command, all your content.</strong>
  </p>
  <p align="center">
    <a href="#memecoin-kit">Memecoin Kit</a> &middot;
    <a href="#quick-start">Quick Start</a> &middot;
    <a href="#what-it-does">What It Does</a> &middot;
    <a href="#all-commands">Commands</a> &middot;
    <a href="#export-presets">Export</a>
  </p>
</p>

---

Tell MuseLoop what you want. It plans it, generates it, critiques it, and keeps improving until it's good. Images, video, audio, editing — handled.

```
You: "make a 30s cyberpunk trailer"

MuseLoop: Plan -> Generate -> Critique -> Revise -> Done
                     ^           |
                     |___________|
                   (keeps going until it's good)
```

Works with **TikTok, YouTube, Twitter/X, Instagram, Dexscreener, pump.fun, Telegram, Discord**.

## Memecoin Kit

Full content kit for your token in one command. Logos, banners, social posts, stickers — everything.

```bash
museloop memecoin "DogWifHat" "WIF" --concept "A dog wearing a hat" --vibe degen
```

That's it. You get:

| Asset | Size | For |
|-------|------|-----|
| Token logo | 1024x1024 | Listings, wallets, aggregators |
| Dexscreener banner | 1500x500 | Pair page |
| pump.fun banner | 800x200 | Token page |
| Twitter header | 1500x500 | Profile banner |
| Twitter PFP | 400x400 | Profile pic |
| Launch announcement | 1200x675 | Twitter post |
| Meme graphic | 1200x675 | Community content |
| Telegram sticker | 512x512 | Sticker pack |
| Discord banner | 960x540 | Server banner |
| Video thumbnail | 1920x1080 | YouTube/social |

### More examples

```bash
# Only specific assets
museloop memecoin "PepeCoin" "PEPE" --vibe retro --chain ETH --assets token_logo,dexscreener_banner

# Just generate the brief (don't run yet)
museloop memecoin "MoonCat" "MCAT" --concept "Cats on the moon" --brief-only

# Custom everything
museloop memecoin "BasedFrog" "BFROG" --vibe neon --chain BASE --tagline "The most based frog on Base"
```

### Vibes

| Vibe | What it looks like |
|------|--------------------|
| `degen` | Green candles, diamond hands, ape energy |
| `cute` | Kawaii, soft colors, wholesome |
| `dark` | Edgy, mysterious, underground |
| `neon` | Cyberpunk, glowing, synthwave |
| `retro` | Pixel art, 8-bit, old internet |

### Memecoin templates

```bash
# Full launch kit — everything above in one shot
museloop run "Launch my memecoin" --template memecoin_launch

# Social content factory — Twitter banners, memes, engagement posts
museloop run "Create viral content for my token" --template memecoin_social

# Hype video — animated logo, promo reel for TikTok/Twitter
museloop run "Make a hype video" --template memecoin_video
```

## Quick Start

```bash
git clone https://github.com/chalkychalk42/MuseLoop.git
cd MuseLoop
uv sync
cp .env.example .env
# add your Anthropic API key to .env
```

Need extras?

```bash
uv sync --extra mcp        # Claude Desktop/Code integration
uv sync --extra web        # Web dashboard
uv sync --extra templates  # YAML workflow templates
uv sync --all-extras       # Everything
```

### Run something

```bash
# From a brief file
museloop run examples/briefs/sci_fi_trailer.json

# From a template
museloop run "Create a TikTok dance video" --template tiktok_vertical

# Memecoin kit
museloop memecoin "DogWifHat" "WIF" --concept "A dog wearing a hat"

# With live progress display
museloop run brief.json --verbose
```

## What It Does

5 AI agents work together in a loop:

1. **Memory** — remembers what worked in previous iterations
2. **Research** — finds style references and prompt tips
3. **Script** — breaks your task into steps
4. **Director** — runs the generation skills (image, video, audio, etc.)
5. **Critic** — scores the output using Claude Vision, gives feedback

If the score is below the threshold, it loops back and tries again with the feedback. If it's good, you're done.

### 9 skills

| Skill | Does | Backends |
|-------|------|----------|
| `image_gen` | Generate images | ComfyUI / Replicate / PIL fallback |
| `flux_gen` | FLUX image gen | diffusers / Replicate |
| `video_gen` | Generate video | CogVideoX / Replicate |
| `audio_gen` | Generate music | AudioCraft / Replicate |
| `editing` | Cut, concat, overlay | ffmpeg |
| `img2img` | Style transfer | ComfyUI / Replicate |
| `tts` | Text to speech | Bark / Replicate |
| `upscale` | Upscale images | Real-ESRGAN / PIL |
| `captions` | Add subtitles | Whisper + ffmpeg |

Every skill tries local first, then cloud API, then a placeholder fallback. It always produces output even with no GPU or API keys.

### 10 templates

| Template | What you get |
|----------|-------------|
| `tiktok_vertical` | TikTok video (9:16) |
| `youtube_shorts` | YouTube Shorts (9:16) |
| `trailer` | Movie/game trailer (16:9) |
| `brand_video` | Brand promo (16:9) |
| `podcast_visual` | Podcast visualizer (16:9) |
| `music_video` | Music video (16:9) |
| `social_carousel` | Multi-image carousel (1:1) |
| `memecoin_launch` | Full token launch kit |
| `memecoin_social` | Social media content factory |
| `memecoin_video` | Hype video / promo reel (9:16) |

```bash
museloop templates              # list all
museloop templates trailer      # inspect one
museloop run "task" --template trailer   # use one
```

## All Commands

```
museloop run <brief>                  Run a pipeline
museloop memecoin <name> <ticker>     Memecoin content kit
museloop skills                       List skills
museloop templates                    List templates
museloop export <file> --preset <p>   Export to platform format
museloop inspect <brief.json>         Preview a brief
museloop history                      Iteration history
museloop serve                        Start MCP server
museloop dashboard                    Web dashboard
museloop version                      Version
```

## Export Presets

Export anything to the right size for any platform.

```bash
museloop export video.mp4 --preset instagram_reels
museloop export logo.png --preset dexscreener_banner --mode fill
museloop export --list   # show all presets
```

**Video platforms:**

| Preset | Size | For |
|--------|------|-----|
| `youtube_1080p` | 1920x1080 | YouTube |
| `youtube_4k` | 3840x2160 | YouTube 4K |
| `instagram_reels` | 1080x1920 | Reels |
| `instagram_square` | 1080x1080 | Posts |
| `tiktok` | 1080x1920 | TikTok |
| `twitter` | 1280x720 | Twitter/X video |

**Crypto platforms:**

| Preset | Size | For |
|--------|------|-----|
| `dexscreener_banner` | 1500x500 | Dexscreener pair banner |
| `dexscreener_icon` | 256x256 | Dexscreener token icon |
| `pumpfun_banner` | 800x200 | pump.fun header |
| `pumpfun_icon` | 400x400 | pump.fun icon |
| `twitter_header` | 1500x500 | Twitter/X banner |
| `twitter_post` | 1200x675 | Twitter/X post |
| `twitter_profile` | 400x400 | Twitter/X PFP |
| `telegram_sticker` | 512x512 | Telegram sticker |
| `discord_banner` | 960x540 | Discord banner |
| `token_logo_sm` | 128x128 | Small logo |
| `token_logo_lg` | 1024x1024 | Large logo |

## MCP Server

Use MuseLoop as a tool inside Claude Desktop or Claude Code.

```bash
museloop serve
```

Add to `claude_desktop_config.json`:

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

Then you can ask Claude to generate images, run pipelines, check job status — all through chat.

## Web Dashboard

```bash
museloop dashboard
# opens at http://127.0.0.1:8420
```

Real-time job monitoring, asset previews, iteration scores, human approval button. Dark theme.

## Config

Copy `.env.example` to `.env`:

```bash
# Required
MUSELOOP_ANTHROPIC_API_KEY=sk-ant-xxxxx

# Optional
MUSELOOP_REPLICATE_API_KEY=r8_xxxxx       # Cloud generation fallback
MUSELOOP_COMFYUI_URL=http://localhost:8188 # Local image gen
MUSELOOP_LLM_BACKEND=claude               # or "openai" for Ollama/vLLM
MUSELOOP_MAX_ITERATIONS=5
MUSELOOP_QUALITY_THRESHOLD=0.7
```

## Docker

```bash
docker compose up                    # With ComfyUI (needs NVIDIA GPU)
docker build -t museloop . && \
docker run --env-file .env museloop run brief.json   # CPU only
```

## Add Your Own Skill

Two files: a Python class and a JSON manifest. Drop them in `src/museloop/skills/` and `manifests/`. Auto-discovered on next run.

```bash
museloop skills   # your skill shows up here
```

See existing skills for examples.

## Dev

```bash
uv sync --all-extras
uv run pytest tests/ -v          # 210 tests
uv run ruff check src/ tests/    # lint
uv run ruff format src/ tests/   # format
```

## License

MIT
