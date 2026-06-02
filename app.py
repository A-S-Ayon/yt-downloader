import os
import re
import yt_dlp
import streamlit as st

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def is_valid_url(url: str) -> bool:
    pattern = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+"
    return bool(re.match(pattern, url.strip()))

def fetch_formats(url: str):
    ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        return None, None, str(e)

    title = info.get("title", "Unknown")
    formats = info.get("formats", [])
    format_map = {}

    for h in [2160, 1440, 1080, 720, 480, 360, 240, 144]:
        candidates = [
            f for f in formats
            if f.get("height") == h
            and f.get("vcodec", "none") != "none"
            and f.get("acodec", "none") != "none"
            and f.get("ext") in ("mp4", "webm")
        ]
        if candidates:
            best = max(candidates, key=lambda f: f.get("tbr") or 0)
            format_map[f"🎬 {h}p MP4 (video+audio)"] = {
                "id": best["format_id"], "audio": False
            }
        else:
            vid = [
                f for f in formats
                if f.get("height") == h
                and f.get("vcodec", "none") != "none"
                and f.get("ext") in ("mp4", "webm")
            ]
            if vid:
                best = max(vid, key=lambda f: f.get("tbr") or 0)
                format_map[f"🎬 {h}p MP4 (merged)"] = {
                    "id": f"{best['format_id']}+bestaudio[ext=m4a]/bestaudio",
                    "audio": False
                }

    format_map["🎵 MP3 Audio (best quality)"] = {
        "id": "bestaudio/best", "audio": True
    }

    return title, format_map, None


def download_video(url: str, fmt_id: str, is_audio: bool):
    outtmpl = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")
    ydl_opts = {
        "format": fmt_id,
        "outtmpl": outtmpl,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": "mp4",
    }

    if is_audio:
        ydl_opts["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]
        ydl_opts.pop("merge_output_format", None)

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        return None, str(e)

    ext = "mp3" if is_audio else "mp4"
    safe_title = yt_dlp.utils.sanitize_filename(info.get("title", "video"))
    file_path = os.path.join(DOWNLOAD_DIR, f"{safe_title}.{ext}")

    if not os.path.exists(file_path):
        candidates = [
            os.path.join(DOWNLOAD_DIR, f)
            for f in os.listdir(DOWNLOAD_DIR)
            if f.endswith(f".{ext}")
        ]
        if candidates:
            file_path = max(candidates, key=os.path.getmtime)
        else:
            return None, "File not found after download"

    return file_path, None


# ── UI ─────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="YT Downloader", page_icon="📥", layout="centered")
st.title("📥 YouTube Downloader")
st.caption("Paste a YouTube URL · Fetch formats · Pick quality · Download")

url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")

if "formats" not in st.session_state:
    st.session_state.formats = {}
if "title" not in st.session_state:
    st.session_state.title = ""

if st.button("🔍 Fetch Formats", type="primary"):
    if not url.strip():
        st.warning("Please enter a URL first.")
    elif not is_valid_url(url):
        st.error("That doesn't look like a valid YouTube URL.")
    else:
        with st.spinner("Fetching available formats..."):
            title, formats, err = fetch_formats(url.strip())
            if err:
                st.error(f"❌ {err}")
            else:
                st.session_state.formats = formats
                st.session_state.title = title
                st.success(f"✅ **{title}** — {len(formats)} formats found")

if st.session_state.formats:
    selected_label = st.selectbox(
        "Available Formats",
        options=list(st.session_state.formats.keys())
    )

    if st.button("⬇️ Download", type="primary"):
        fmt = st.session_state.formats[selected_label]
        with st.spinner("Downloading... this may take a while for large files"):
            file_path, err = download_video(url.strip(), fmt["id"], fmt["audio"])
            if err:
                st.error(f"❌ {err}")
            else:
                with open(file_path, "rb") as f:
                    ext = "mp3" if fmt["audio"] else "mp4"
                    mime = "audio/mpeg" if fmt["audio"] else "video/mp4"
                    st.download_button(
                        label=f"💾 Save {os.path.basename(file_path)}",
                        data=f,
                        file_name=os.path.basename(file_path),
                        mime=mime
                    )
                st.success("Ready! Click the button above to save.")

st.divider()
st.caption(
    "⚠️ For personal/educational use only. "
    "Respect YouTube's Terms of Service and content creators' rights."
)