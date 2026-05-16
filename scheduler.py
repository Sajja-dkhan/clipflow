import os
import threading
from datetime import datetime, timezone
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

import config
from modules import ensure_db, load_db, save_db
from modules.storage_manager import cleanup_old_clips, cleanup_old_video

scheduler = BackgroundScheduler()

job_status = {"state": "idle", "progress": 0, "message": ""}
_job_lock = threading.Lock()
_run_lock = threading.Lock()


def _set_status(state: str, progress: int, message: str) -> None:
    with _job_lock:
        job_status["state"] = state
        job_status["progress"] = progress
        job_status["message"] = message


def _default_style(db: dict) -> dict:
    settings = db.get("settings", {})
    return {
        "caption_font": config.CAPTION_FONT,
        "caption_font_size": settings.get("caption_font_size", config.CAPTION_FONT_SIZE),
        "caption_color": settings.get("caption_color", config.CAPTION_COLOR),
        "caption_background": settings.get("caption_background", config.CAPTION_BG_COLOR),
        "caption_position": settings.get("caption_position", config.CAPTION_POSITION),
        "whisper_model": settings.get("whisper_model", config.WHISPER_MODEL),
    }


def daily_check() -> None:
    if not _run_lock.acquire(blocking=False):
        return

    try:
        from modules.caption_generator import process_all_clips
        from modules.clip_extractor import extract_clips
        from modules.youtube_handler import (
            download_video,
            get_latest_video_via_api,
            get_latest_video_via_ytdlp,
        )

        ensure_db()
        db = load_db()
        channel = db.get("channel", {})
        channel_url = channel.get("url")
        channel_id = channel.get("channel_id")

        if not channel_url:
            _set_status("idle", 0, "No channel configured")
            return

        _set_status("checking", 5, "Checking for latest video")
        api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
        latest = None

        if api_key and channel_id:
            latest = get_latest_video_via_api(channel_id, api_key)

        if not latest:
            latest = get_latest_video_via_ytdlp(channel_url)

        if not latest or not latest.get("video_id"):
            _set_status("idle", 0, "Could not fetch latest video")
            return

        latest_video_id = latest["video_id"]
        if any(v.get("video_id") == latest_video_id for v in db.get("videos", [])):
            db["last_check"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            save_db(db)
            _set_status("done", 100, "No new video found")
            return

        _set_status("downloading", 20, "Downloading latest video")
        downloaded = download_video(latest_video_id, config.DOWNLOAD_DIR)
        if not downloaded:
            _set_status("idle", 0, "Failed to download video")
            return

        clip_output_dir = os.path.join(config.CLIPS_DIR, latest_video_id)
        _set_status("extracting", 45, "Extracting clips")
        clips = extract_clips(
            downloaded,
            clip_output_dir,
            min_duration=config.MIN_CLIP_DURATION,
            max_duration=config.MAX_CLIP_DURATION,
        )
        if not clips:
            _set_status("idle", 0, "No clips extracted")
            return

        _set_status("captioning", 70, "Downloading AI model for the first time, please wait...")
        final_output_dir = os.path.join(config.FINAL_CLIPS_DIR, latest_video_id)
        final_paths = process_all_clips(clips, final_output_dir, _default_style(load_db()))

        db = load_db()
        for video in db.get("videos", []):
            if video.get("video_id") == latest_video_id:
                video["title"] = video.get("title") or latest.get("title", "")
                for clip in video.get("clips", []):
                    clip_name = os.path.splitext(os.path.basename(clip.get("clip_path", "")))[0]
                    final_match = next((fp for fp in final_paths if os.path.basename(fp).startswith(clip_name)), "")
                    clip["final_path"] = final_match
                    clip["caption_status"] = "done" if final_match else "failed"
                video["status"] = "completed"
                break

        db["last_check"] = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        save_db(db)

        cleanup_old_video(keep_video_id=latest_video_id)
        cleanup_old_clips(keep_video_id=latest_video_id)

        _set_status("done", 100, "Processing completed")
    except Exception as exc:
        _set_status("idle", 0, f"Error: {exc}")
    finally:
        _run_lock.release()


def run_check_async() -> bool:
    if _run_lock.locked():
        return False
    thread = threading.Thread(target=daily_check, daemon=True)
    thread.start()
    return True


def _schedule_time_from_db() -> tuple[int, int]:
    try:
        db = load_db()
        schedule_time = db.get("settings", {}).get("schedule_time", "09:00")
        hour_str, minute_str = schedule_time.split(":", 1)
        return int(hour_str), int(minute_str)
    except Exception:
        return config.SCHEDULE_HOUR, config.SCHEDULE_MINUTE


def start_scheduler() -> None:
    if scheduler.running:
        return
    hour, minute = _schedule_time_from_db()
    scheduler.add_job(daily_check, "cron", hour=hour, minute=minute, id="daily_check", replace_existing=True)
    scheduler.start()


def reschedule_daily_job(hour: int, minute: int) -> None:
    scheduler.add_job(daily_check, "cron", hour=hour, minute=minute, id="daily_check", replace_existing=True)
