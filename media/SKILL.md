---
name: media
description: "Media content toolkit: search GIFs, analyze audio spectrograms, and extract/transform YouTube transcripts. Two core patterns — API fetch (curl/jq) and CLI analysis."
metadata:
  hermes:
    tags: [media, GIF, audio, YouTube, transcript, spectrogram]
    related_skills: []
---

# Media Content Toolkit

Three tools for finding, analyzing, and repurposing media content.

## Tool Router

| Task | Tool | Pattern |
|------|------|---------|
| Find a reaction GIF | Tenor API | `curl + jq` — see `references/gif-search.md` |
| Analyze audio features | `songsee` | Go CLI — see `references/songsee.md` |
| Summarize a YouTube video | `youtube-transcript-api` | Python script — see `references/youtube-content.md` |

## Common Patterns

### Pattern A: API Fetch (curl + jq)

Used by GIF search and reusable for any JSON API:

```bash
# Fetch + extract field
curl -s "https://api.example.com/endpoint?key=$API_KEY" | jq -r '.results[].field'

# Fetch + structured filter
curl -s "..." | jq '.results[] | {name: .title, url: .link}'
```

Always URL-encode queries (spaces → `+`, special chars → `%XX`).

### Pattern B: Python Script Helper

Used by YouTube transcript extraction. Reusable pattern for any pip-installable tool:

```bash
pip install <package>
python3 scripts/<helper>.py "<input>" --text-only
```

### Pattern C: CLI Visualization

Used by songsee for audio analysis. Reusable for any single-binary CLI tool:

```bash
# Install
go install github.com/user/tool@latest

# Run with flags
tool input.mp3 --viz type1,type2 -o output.png
```

---

## Workflow 1: Search & Download Media

For reaction GIFs, visual content, or lightweight media:

```bash
# Set API key in ~/.hermes/.env: TENOR_API_KEY=...
source ~/.hermes/.env

# Search and get direct URL
curl -s "https://tenor.googleapis.com/v2/search?q=celebration&limit=3&key=$TENOR_API_KEY" \
  | jq -r '.results[].media_formats.gif.url'

# Download top result
URL=$(curl -s "...search...limit=1..." | jq -r '.results[0].media_formats.gif.url')
curl -sL "$URL" -o output.gif
```

For full parameters, media formats, and metadata — `references/gif-search.md`.

---

## Workflow 2: Audio Analysis

Generate spectrograms and feature visualizations from audio files:

```bash
# Basic spectrogram
songsee track.mp3 -o spectrogram.png

# Multi-panel grid (mel, chroma, MFCC, tempo, loudness, flux)
songsee track.mp3 --viz spectrogram,mel,chroma,mfcc,tempogram,loudness,flux -o analysis.png

# Time slice
songsee track.mp3 --start 12.5 --duration 8 -o slice.png
```

For all visualization types, color palettes, and FFT tuning — `references/songsee.md`.

---

## Workflow 3: YouTube Transcript Extraction

Fetch transcripts and transform them into structured content:

```bash
pip install youtube-transcript-api

# Fetch with timestamps
python3 scripts/fetch_transcript.py "URL" --text-only --timestamps

# Specific language with fallback
python3 scripts/fetch_transcript.py "URL" --language ja,en
```

**Transform the output based on user request:**
- **Summary** → concise 5-10 sentence overview
- **Chapters** → timestamped topic shifts
- **Thread** → numbered posts under 280 chars
- **Blog post** → full article with sections
- **Quotes** → notable quotes with timestamps

For error handling (disabled transcripts, private videos, language fallback) and the full transformation guide — `references/youtube-content.md`.
