import os
from typing import Dict, List, Tuple

import ffmpeg
from scenedetect import SceneManager, open_video
from scenedetect.detectors import ContentDetector

from modules import load_db, save_db


def _scene_to_seconds(scene_pair: Tuple) -> Tuple[float, float]:
    return float(scene_pair[0].get_seconds()), float(scene_pair[1].get_seconds())


def _merge_and_split_scenes(raw_scenes: List[Tuple[float, float]], min_duration: int, max_duration: int) -> List[Tuple[float, float]]:
    merged: List[Tuple[float, float]] = []
    i = 0
    while i < len(raw_scenes):
        start, end = raw_scenes[i]
        duration = end - start
        if duration < min_duration and i + 1 < len(raw_scenes):
            next_start, next_end = raw_scenes[i + 1]
            merged.append((start, next_end))
            i += 2
            continue
        if duration < min_duration and merged:
            prev_start, _ = merged[-1]
            merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))
        i += 1

    split: List[Tuple[float, float]] = []
    for start, end in merged:
        cursor = start
        while (end - cursor) > max_duration:
            split.append((cursor, cursor + max_duration))
            cursor += max_duration
        if (end - cursor) >= min_duration:
            split.append((cursor, end))
    return split


def extract_clips(video_path: str, output_dir: str, min_duration: int = 10, max_duration: int = 60) -> List[Dict]:
    try:
        os.makedirs(output_dir, exist_ok=True)

        video = open_video(video_path)
        scene_manager = SceneManager()
        scene_manager.add_detector(ContentDetector(threshold=30.0))
        scene_manager.detect_scenes(video)
        scenes = scene_manager.get_scene_list()

        if scenes:
            raw = [_scene_to_seconds(s) for s in scenes]
        else:
            probe = ffmpeg.probe(video_path)
            duration = float(probe["format"]["duration"])
            raw = [(0.0, duration)]

        ranges = _merge_and_split_scenes(raw, min_duration=min_duration, max_duration=max_duration)
        clips: List[Dict] = []

        for idx, (start, end) in enumerate(ranges, start=1):
            clip_path = os.path.join(output_dir, f"clip_{idx:03d}.mp4")
            (
                ffmpeg
                .input(video_path, ss=start, to=end)
                .output(clip_path, c="copy")
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            clips.append(
                {
                    "clip_path": clip_path.replace("\\", "/"),
                    "start_time": round(start, 2),
                    "end_time": round(end, 2),
                    "duration": round(end - start, 2),
                    "clip_number": idx,
                }
            )

        video_id = os.path.splitext(os.path.basename(video_path))[0]
        db = load_db()
        for video_entry in db.get("videos", []):
            if video_entry.get("video_id") == video_id:
                video_entry["clips"] = [
                    {
                        **clip,
                        "final_path": "",
                        "caption_status": "pending",
                        "deleted": False,
                    }
                    for clip in clips
                ]
                video_entry["status"] = "clips_extracted"
                break
        save_db(db)

        return clips
    except Exception:
        return []
