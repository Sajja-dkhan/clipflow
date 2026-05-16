import os
import shutil
from typing import Dict, Optional

from config import CLIPS_DIR, DOWNLOAD_DIR, FINAL_CLIPS_DIR
from modules import load_db, save_db


def _folder_size_mb(path: str) -> float:
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            file_path = os.path.join(root, name)
            if os.path.exists(file_path):
                total += os.path.getsize(file_path)
    return round(total / (1024 * 1024), 2)


def cleanup_old_video(keep_video_id: Optional[str] = None) -> None:
    try:
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        for file_name in os.listdir(DOWNLOAD_DIR):
            if not file_name.lower().endswith(".mp4"):
                continue
            if keep_video_id and keep_video_id in file_name:
                continue
            os.remove(os.path.join(DOWNLOAD_DIR, file_name))
    except Exception:
        return


def cleanup_old_clips(keep_video_id: Optional[str] = None) -> None:
    try:
        os.makedirs(CLIPS_DIR, exist_ok=True)
        for entry in os.listdir(CLIPS_DIR):
            full_path = os.path.join(CLIPS_DIR, entry)
            if keep_video_id and entry == keep_video_id:
                continue
            if os.path.isdir(full_path):
                shutil.rmtree(full_path, ignore_errors=True)
    except Exception:
        return


def get_disk_usage() -> Dict[str, float]:
    try:
        downloads = _folder_size_mb(DOWNLOAD_DIR)
        clips = _folder_size_mb(CLIPS_DIR)
        final = _folder_size_mb(FINAL_CLIPS_DIR)
        return {
            "downloads_size_mb": downloads,
            "clips_size_mb": clips,
            "final_clips_size_mb": final,
            "total_size_mb": round(downloads + clips + final, 2),
        }
    except Exception:
        return {
            "downloads_size_mb": 0,
            "clips_size_mb": 0,
            "final_clips_size_mb": 0,
            "total_size_mb": 0,
        }


def user_delete_clip(clip_path: str) -> bool:
    try:
        if not clip_path:
            return False
        db = load_db()
        matched_path = ""
        for video in db.get("videos", []):
            for clip in video.get("clips", []):
                if clip.get("final_path") == clip_path:
                    matched_path = clip.get("final_path", "")
                    break
            if matched_path:
                break

        if not matched_path:
            return False

        requested_path = os.path.abspath(matched_path)
        allowed_root = os.path.abspath(FINAL_CLIPS_DIR)
        if os.path.commonpath([requested_path, allowed_root]) != allowed_root:
            return False
        if os.path.exists(requested_path):
            os.remove(requested_path)

        for video in db.get("videos", []):
            for clip in video.get("clips", []):
                if clip.get("final_path") == clip_path or clip.get("clip_path") == clip_path:
                    clip["deleted"] = True
                    clip["caption_status"] = "deleted"
                    if clip.get("final_path") == clip_path:
                        clip["final_path"] = ""
        save_db(db)
        return True
    except Exception:
        return False
