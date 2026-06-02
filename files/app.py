"""
YouTube Downloader — Gradio Web App
Backend: yt-dlp + ffmpeg
Deployment: Hugging Face Spaces (Gradio SDK)
"""

import os
import re
import gradio as gr
import yt_dlp

# ── Constants ──────────────────────────────────────────────────────────────────
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ── Helpers ────────────────────────────────────────────────────────────────────

def is_valid_youtube_url(url: str) -> bool:
    """Loosely validate that the URL looks like a YouTube link."""
    pattern = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+"
    return bool(re.match(pattern, url.strip()))


def fetch_formats(url: str):
    """
    Query yt-dlp for available formats and return:
      - A human-readable list of format labels  (for the dropdown)
      - A dict mapping label → yt-dlp format string
      - A status message
    """
    url = url.strip()

    if not url:
        return gr.update(choices=[], value=None), {}, "⚠️ Please paste a YouTube URL first."

    if not is_valid_youtube_url(url):
        return gr.update(choices=[], value=None), {}, "❌ That doesn't look like a valid YouTube URL."

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as e:
        return gr.update(choices=[], value=None), {}, f"❌ Could not fetch video info:\n{e}"
    except Exception as e:
        return gr.update(choices=[], value=None), {}, f"❌ Unexpected error: {e}"

    title = info.get("title", "Unknown title")
    formats = info.get("formats", [])

    # Build a deduplicated set of useful video+audio options
    seen_heights = set()
    format_map = {}  # label → yt-dlp format selector

    # Prefer formats that have both video and audio merged; fall back to best video+bestaudio
    target_heights = [2160, 1440, 1080, 720, 480, 360, 240, 144]

    for h in target_heights:
        # Find the best combined format at this height (vcodec + acodec both set)
        candidates = [
            f for f in formats
            if f.get("height") == h
            and f.get("vcodec", "none") != "none"
            and f.get("acodec", "none") != "none"
            and f.get("ext") in ("mp4", "webm")
        ]
        if candidates:
            best = max(candidates, key=lambda f: f.get("tbr") or 0)
            label = f"🎬 {h}p MP4 (video+audio)"
            format_map[label] = best["format_id"]
            seen_heights.add(h)
        else:
            # Try video-only + merge with bestaudio via ffmpeg
            vid_candidates = [
                f for f in formats
                if f.get("height") == h
                and f.get("vcodec", "none") != "none"
                and f.get("ext") in ("mp4", "webm")
            ]
            if vid_candidates:
                best = max(vid_candidates, key=lambda f: f.get("tbr") or 0)
                label = f"🎬 {h}p MP4 (merged)"
                format_map[label] = f"{best['format_id']}+bestaudio[ext=m4a]/bestaudio"
                seen_heights.add(h)

    # Always add MP3 audio option
    format_map["🎵 MP3 Audio (best quality)"] = "bestaudio/best"

    if not format_map:
        return gr.update(choices=[], value=None), {}, "⚠️ No usable formats found for this video."

    choices = list(format_map.keys())
    status = f"✅ **{title}**\nFound {len(choices)} format(s). Select one and click Download."

    return gr.update(choices=choices, value=choices[0]), format_map, status


def download_video(url: str, selected_label: str, format_map: dict):
    """
    Download the video/audio in the chosen format.
    Returns a file path (for Gradio File output) and a status message.
    """
    url = url.strip()

    if not url or not is_valid_youtube_url(url):
        return None, "❌ Invalid URL. Please fetch formats first."

    if not selected_label or not format_map:
        return None, "⚠️ Please fetch formats and select one before downloading."

    fmt_selector = format_map.get(selected_label)
    if not fmt_selector:
        return None, "❌ Format not found. Try fetching formats again."

    is_audio = "MP3" in selected_label

    # Output template: downloads/<video_title>.<ext>
    outtmpl = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    ydl_opts = {
        "format": fmt_selector,
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",       # merge video+audio into mp4
    }

    if is_audio:
        # Extract audio and convert to mp3
        ydl_opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ]
        # Remove merge_output_format when doing audio extraction
        ydl_opts.pop("merge_output_format", None)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except yt_dlp.utils.DownloadError as e:
        return None, f"❌ Download failed:\n{e}"
    except Exception as e:
        return None, f"❌ Unexpected error during download:\n{e}"

    # Resolve the actual output path
    title = info.get("title", "video")
    ext = "mp3" if is_audio else "mp4"

    # yt-dlp sanitises titles; replicate its sanitisation to find the file
    safe_title = yt_dlp.utils.sanitize_filename(title)
    file_path = os.path.join(DOWNLOAD_DIR, f"{safe_title}.{ext}")

    # Fallback: scan downloads dir for the most recently modified matching file
    if not os.path.exists(file_path):
        candidates = [
            os.path.join(DOWNLOAD_DIR, f)
            for f in os.listdir(DOWNLOAD_DIR)
            if f.endswith(f".{ext}")
        ]
        if candidates:
            file_path = max(candidates, key=os.path.getmtime)
        else:
            return None, "⚠️ Download seemed to succeed but file not found. Check the downloads/ folder."

    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    status = f"✅ Downloaded: **{os.path.basename(file_path)}** ({size_mb:.1f} MB)"
    return file_path, status


# ── Gradio UI ──────────────────────────────────────────────────────────────────

def build_ui():
    with gr.Blocks(
        title="YT Downloader",
        theme=gr.themes.Soft(primary_hue="red", secondary_hue="gray"),
        css="""
            #title { text-align: center; }
            #subtitle { text-align: center; color: #888; margin-top: -8px; }
            .gr-button-primary { background: #ff0000 !important; border-color: #cc0000 !important; }
        """,
    ) as demo:

        # ── Header ─────────────────────────────────────────────────────────────
        gr.Markdown("# 📥 YouTube Downloader", elem_id="title")
        gr.Markdown(
            "Paste a YouTube URL · Fetch formats · Pick quality · Download",
            elem_id="subtitle",
        )

        # ── Hidden state: format map ───────────────────────────────────────────
        format_map_state = gr.State({})

        # ── Row 1: URL input ───────────────────────────────────────────────────
        with gr.Row():
            url_input = gr.Textbox(
                label="YouTube URL",
                placeholder="https://www.youtube.com/watch?v=...",
                scale=4,
            )
            fetch_btn = gr.Button("🔍 Fetch Formats", variant="primary", scale=1)

        # ── Status line ────────────────────────────────────────────────────────
        status_box = gr.Markdown("_Paste a URL and click Fetch Formats to begin._")

        # ── Row 2: Format selector + download ─────────────────────────────────
        with gr.Row():
            format_dropdown = gr.Dropdown(
                label="Available Formats",
                choices=[],
                interactive=True,
                scale=4,
            )
            download_btn = gr.Button("⬇️ Download", variant="primary", scale=1)

        # ── Output: file download widget ───────────────────────────────────────
        output_file = gr.File(label="Your file is ready 👇", visible=False)

        # ── Wire up events ─────────────────────────────────────────────────────
        fetch_btn.click(
            fn=fetch_formats,
            inputs=[url_input],
            outputs=[format_dropdown, format_map_state, status_box],
        )

        def handle_download(url, selected_label, fmt_map):
            file_path, msg = download_video(url, selected_label, fmt_map)
            file_update = gr.update(value=file_path, visible=file_path is not None)
            return file_update, msg

        download_btn.click(
            fn=handle_download,
            inputs=[url_input, format_dropdown, format_map_state],
            outputs=[output_file, status_box],
        )

        # ── Footer ─────────────────────────────────────────────────────────────
        gr.Markdown(
            "---\n"
            "⚠️ **For personal/educational use only.** "
            "Respect YouTube's [Terms of Service](https://www.youtube.com/t/terms) "
            "and content creators' rights.",
            elem_id="footer",
        )

    return demo


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = build_ui()
    # share=False for local; Hugging Face Spaces launches automatically
    app.launch()
