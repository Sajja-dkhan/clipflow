import os
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS

import config
from modules import ensure_db, load_db
from modules.storage_manager import get_disk_usage, user_delete_clip
from scheduler import job_status, reschedule_daily_job, run_check_async, start_scheduler

load_dotenv()

app = Flask(__name__)
CORS(app)

ensure_db()
start_scheduler()


@app.get("/")
def index():
    db = load_db()
    latest_video = db.get("videos", [])[-1] if db.get("videos") else None
    return render_template(
        "index.html",
        channel=db.get("channel", {}),
        last_check=db.get("last_check", ""),
        latest_video=latest_video,
        disk_usage=get_disk_usage(),
    )


@app.get("/channel")
def channel_page():
    db = load_db()
    return render_template("channel.html", channel=db.get("channel", {}))


@app.post("/api/channel/save")
def save_channel():
    try:
        from modules.youtube_handler import extract_channel_id

        payload = request.get_json(silent=True) or request.form.to_dict()
        channel_url = (payload.get("channel_url") or "").strip()
        api_key = (payload.get("api_key") or "").strip() or os.getenv("YOUTUBE_API_KEY", "").strip()

        channel_id = extract_channel_id(channel_url, api_key=api_key or None)
        if not channel_id:
            return jsonify({"success": False, "message": "Unable to resolve channel id"}), 400

        db = load_db()
        db["channel"] = {
            "url": channel_url,
            "channel_id": channel_id,
            "name": channel_url.rstrip("/").split("/")[-1].lstrip("@") or channel_id,
            "added_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
        save_db(db)
        return jsonify({"success": True, "channel": db["channel"]})
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@app.post("/api/channel/check-now")
def check_now():
    started = run_check_async()
    if not started:
        return jsonify({"success": False, "message": "A job is already running"}), 409
    return jsonify({"success": True, "message": "Check started"})


@app.get("/api/status")
def status():
    return jsonify(job_status)


@app.get("/clips")
def clips_page():
    db = load_db()
    return render_template("clips.html", videos=db.get("videos", []))


@app.get("/api/clips")
def clips_api():
    db = load_db()
    return jsonify({"videos": db.get("videos", [])})


@app.post("/api/clips/delete")
def delete_clip_api():
    payload = request.get_json(silent=True) or {}
    clip_path = payload.get("clip_path", "")
    success = user_delete_clip(clip_path)
    return jsonify({"success": success})


@app.get("/api/disk-usage")
def disk_usage_api():
    return jsonify(get_disk_usage())


@app.get("/settings")
def settings_page():
    db = load_db()
    return render_template("settings.html", settings=db.get("settings", {}))


@app.post("/api/settings/save")
def save_settings():
    try:
        payload = request.get_json(silent=True) or request.form.to_dict()
        db = load_db()
        settings = db.setdefault("settings", {})
        settings["caption_font_size"] = int(payload.get("caption_font_size", settings.get("caption_font_size", config.CAPTION_FONT_SIZE)))
        settings["caption_position"] = payload.get("caption_position", settings.get("caption_position", config.CAPTION_POSITION))
        settings["caption_color"] = payload.get("caption_color", settings.get("caption_color", config.CAPTION_COLOR))
        settings["caption_background"] = payload.get("caption_background", settings.get("caption_background", config.CAPTION_BG_COLOR))
        settings["whisper_model"] = payload.get("whisper_model", settings.get("whisper_model", config.WHISPER_MODEL))
        schedule_time = payload.get("schedule_time", settings.get("schedule_time", "09:00"))
        settings["schedule_time"] = schedule_time

        try:
            hour_str, minute_str = schedule_time.split(":", 1)
            reschedule_daily_job(int(hour_str), int(minute_str))
        except Exception:
            pass

        save_db(db)
        return jsonify({"success": True, "settings": settings})
    except Exception as exc:
        return jsonify({"success": False, "message": str(exc)}), 500


@app.get("/data/clips_with_captions/<path:clip_file>")
def serve_final_clip(clip_file):
    return send_from_directory(config.FINAL_CLIPS_DIR, clip_file, as_attachment=False)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
