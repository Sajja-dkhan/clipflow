import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, urlparse

import requests
import yt_dlp

from modules import load_db, save_db


YOUTUBE_SEARCH_API = "https://www.googleapis.com/youtube/v3/search"


def _safe_video_entry(item: Dict[str, Any]) -> Dict[str, str]:
    snippet = item.get("snippet", {})
    thumbnails = snippet.get("thumbnails", {})
    thumb = thumbnails.get("high") or thumbnails.get("medium") or thumbnails.get("default") or {}
    return {
        "video_id": item.get("id", {}).get("videoId", ""),
        "title": snippet.get("title", ""),
        "published_at": snippet.get("publishedAt", ""),
        "thumbnail_url": thumb.get("url", ""),
        "description": snippet.get("description", ""),
    }


def get_latest_video_via_api(channel_id: str, api_key: str) -> Optional[Dict[str, str]]:
    try:
        params = {
            "part": "snippet",
            "channelId": channel_id,
            "order": "date",
            "maxResults": 1,
            "type": "video",
            "key": api_key,
        }
        response = requests.get(YOUTUBE_SEARCH_API, params=params, timeout=20)
        response.raise_for_status()
        items = response.json().get("items", [])
        if not items:
            return None
        return _safe_video_entry(items[0])
    except Exception:
        return None


def get_latest_video_via_ytdlp(channel_url: str) -> Optional[Dict[str, str]]:
    try:
        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
            "playlistend": 1,
        }
        browser = os.getenv("YTDLP_COOKIES_BROWSER", "").strip()
        if browser:
            ydl_opts["cookiesfrombrowser"] = (browser,)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)

        entries = info.get("entries") or []
        if not entries:
            return None

        latest = entries[0]
        thumb = latest.get("thumbnail") or ""
        return {
            "video_id": latest.get("id", ""),
            "title": latest.get("title", ""),
            "published_at": latest.get("upload_date", ""),
            "thumbnail_url": thumb,
            "description": latest.get("description", ""),
        }
    except Exception:
        return None


def download_video(video_id: str, output_dir: str) -> Optional[str]:
    os.makedirs(output_dir, exist_ok=True)
    downloaded_path = None
    info_holder: Dict[str, Any] = {}

    def _progress_hook(data: Dict[str, Any]) -> None:
        nonlocal downloaded_path
        if data.get("status") == "finished":
            downloaded_path = data.get("filename")

    try:
        ydl_opts = {
            "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
            "outtmpl": os.path.join(output_dir, "%(id)s.%(ext)s"),
            "progress_hooks": [_progress_hook],
            "quiet": True,
            "noplaylist": True,
            "merge_output_format": "mp4",
        }

        browser = os.getenv("YTDLP_COOKIES_BROWSER", "").strip()
        if browser:
            ydl_opts["cookiesfrombrowser"] = (browser,)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_holder = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=True)
            if not downloaded_path:
                downloaded_path = ydl.prepare_filename(info_holder)
                base, _ = os.path.splitext(downloaded_path)
                mp4_path = f"{base}.mp4"
                if os.path.exists(mp4_path):
                    downloaded_path = mp4_path

        if not downloaded_path:
            return None

        db = load_db()
        existing = next((v for v in db.get("videos", []) if v.get("video_id") == video_id), None)
        if existing is None:
            db.setdefault("videos", []).append(
                {
                    "video_id": video_id,
                    "title": info_holder.get("title", ""),
                    "downloaded_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                    "file_path": downloaded_path.replace("\\", "/"),
                    "status": "downloaded",
                    "clips": [],
                }
            )
        else:
            existing["file_path"] = downloaded_path.replace("\\", "/")
            existing["status"] = "downloaded"
            existing["downloaded_at"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            if info_holder.get("title"):
                existing["title"] = info_holder.get("title")

        save_db(db)
        return downloaded_path
    except Exception:
        return None


def extract_channel_id(channel_url: str, api_key: Optional[str] = None) -> Optional[str]:
    try:
        parsed = urlparse(channel_url)
        path_parts = [p for p in parsed.path.split("/") if p]
        if len(path_parts) >= 2 and path_parts[0].lower() == "channel":
            return path_parts[1]

        normalized_netloc = parsed.netloc.lower()
        if normalized_netloc in {"youtube.com", "www.youtube.com", "m.youtube.com"} and parsed.path == "/watch":
            query = parse_qs(parsed.query)
            if "v" in query:
                return None

        if api_key:
            try:
                query_text = path_parts[-1].lstrip("@") if path_parts else channel_url
                response = requests.get(
                    YOUTUBE_SEARCH_API,
                    params={
                        "part": "snippet",
                        "q": query_text,
                        "type": "channel",
                        "maxResults": 1,
                        "key": api_key,
                    },
                    timeout=20,
                )
                response.raise_for_status()
                items = response.json().get("items", [])
                if items:
                    channel_id = items[0].get("snippet", {}).get("channelId") or items[0].get("id", {}).get("channelId")
                    if channel_id:
                        return channel_id
            except Exception:
                pass

        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": True,
        }
        browser = os.getenv("YTDLP_COOKIES_BROWSER", "").strip()
        if browser:
            ydl_opts["cookiesfrombrowser"] = (browser,)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)

        return info.get("channel_id") or info.get("uploader_id")
    except Exception:
        return None
