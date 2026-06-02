# 📥 YouTube Downloader

A clean, browser-based YouTube downloader built with **Gradio** + **yt-dlp** + **ffmpeg**.

Paste any YouTube URL, choose your quality (1080p, 720p, 360p … or MP3 audio), and download the file directly from your browser.

---

## Features

- Fetches all available video qualities (MP4) and audio (MP3)
- Merges video + audio streams automatically via ffmpeg when needed
- Graceful error handling (invalid URLs, unavailable videos, network issues)
- Works locally and deploys to Hugging Face Spaces with zero config changes

---

## Local Setup

### Prerequisites

| Tool | Install |
|------|---------|
| Python ≥ 3.9 | [python.org](https://www.python.org/downloads/) |
| ffmpeg | See below |
| pip | Comes with Python |

#### Install ffmpeg

**macOS (Homebrew)**
```bash
brew install ffmpeg
```

**Ubuntu / Debian**
```bash
sudo apt update && sudo apt install ffmpeg -y
```

**Windows**
Download a build from [ffmpeg.org](https://ffmpeg.org/download.html) and add it to your `PATH`.

---

### Run the App

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/yt-downloader.git
cd yt-downloader

# 2. Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Launch
python app.py
```

Open your browser at **http://127.0.0.1:7860** — the app will be waiting.

Downloaded files are saved to the `downloads/` folder (auto-created on first run).

---

## Deploy to Hugging Face Spaces

Hugging Face Spaces natively supports Gradio apps. Follow these steps:

### 1. Create a new Space

1. Go to [huggingface.co/new-space](https://huggingface.co/new-space)
2. Choose **Gradio** as the SDK
3. Set visibility to *Public* or *Private*

### 2. Handle ffmpeg on Spaces

Hugging Face Spaces (Linux containers) supports a `packages.txt` file to install system packages via `apt`. Create a `packages.txt` file in the root of your repo:

```
ffmpeg
```

Spaces will run `apt-get install ffmpeg` automatically before starting the app.

### 3. Push your code

```bash
# Add the Spaces remote (replace with your Space URL)
git remote add space https://huggingface.co/spaces/YOUR_USERNAME/yt-downloader

git push space main
```

Or use the Hugging Face web UI to upload files directly.

### 4. That's it

Spaces detects `app.py` + `requirements.txt`, installs everything, and launches. Your app will be live at:

```
https://huggingface.co/spaces/YOUR_USERNAME/yt-downloader
```

---

## Project Structure

```
yt-downloader/
├── app.py            ← Gradio UI + yt-dlp download logic
├── requirements.txt  ← Python dependencies
├── packages.txt      ← System packages for Hugging Face Spaces (add ffmpeg here)
├── README.md         ← You are here
└── .gitignore
```

---

## ⚠️ Legal Notice

This tool is intended for **personal and educational use only**.  
Please respect [YouTube's Terms of Service](https://www.youtube.com/t/terms) and the rights of content creators.  
Do not use this tool to download copyrighted content without permission.

---

## Tech Stack

| Layer | Library |
|-------|---------|
| UI | [Gradio](https://gradio.app) |
| Download engine | [yt-dlp](https://github.com/yt-dlp/yt-dlp) |
| Audio/video muxing | [ffmpeg](https://ffmpeg.org) |
| Language | Python 3.9+ |
