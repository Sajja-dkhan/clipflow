import os
import subprocess
from typing import Dict, List, Optional

import whisper

_MODEL_CACHE = {}


def _format_srt_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _load_model(model_name: str):
    if model_name not in _MODEL_CACHE:
        _MODEL_CACHE[model_name] = whisper.load_model(model_name)
    return _MODEL_CACHE[model_name]


def _escape_subtitle_path_for_ffmpeg(path: str) -> str:
    normalized = os.path.abspath(path).replace("\\", "/")
    escaped = normalized.replace(":", "\\:").replace("'", "\\'")
    return escaped


def generate_captions_for_clip(clip_path: str, output_dir: str, style_config: Dict) -> Optional[str]:
    try:
        os.makedirs(output_dir, exist_ok=True)
        model_name = style_config.get("whisper_model", "base")
        model = _load_model(model_name)
        result = model.transcribe(clip_path)

        base_name = os.path.splitext(os.path.basename(clip_path))[0]
        srt_path = os.path.join(output_dir, f"{base_name}.srt")

        with open(srt_path, "w", encoding="utf-8") as fh:
            for idx, segment in enumerate(result.get("segments", []), start=1):
                start = _format_srt_time(float(segment["start"]))
                end = _format_srt_time(float(segment["end"]))
                text = segment.get("text", "").strip()
                fh.write(f"{idx}\n{start} --> {end}\n{text}\n\n")

        return srt_path
    except Exception:
        return None


def burn_captions_into_clip(clip_path: str, srt_path: str, output_path: str, style_config: Dict) -> Optional[str]:
    try:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        position = style_config.get("caption_position", "bottom").lower()
        alignment = 6 if position == "top" else 2
        font = style_config.get("caption_font", "Arial")
        size = int(style_config.get("caption_font_size", 24))

        subtitle_path = _escape_subtitle_path_for_ffmpeg(srt_path)
        vf = (
            f"subtitles={subtitle_path}:"
            f"force_style='FontName={font},FontSize={size},PrimaryColour=&H00FFFFFF,BackColour=&H80000000,Alignment={alignment}'"
        )

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                clip_path,
                "-vf",
                vf,
                "-c:a",
                "copy",
                output_path,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return output_path
    except Exception:
        return None


def process_all_clips(clips_list: List[Dict], output_dir: str, style_config: Dict) -> List[str]:
    final_paths: List[str] = []
    try:
        for clip in clips_list:
            clip_path = clip.get("clip_path")
            if not clip_path:
                continue
            srt_path = generate_captions_for_clip(clip_path, os.path.dirname(clip_path), style_config)
            if not srt_path:
                continue
            base_name = os.path.splitext(os.path.basename(clip_path))[0]
            output_path = os.path.join(output_dir, f"{base_name}_captioned.mp4")
            final = burn_captions_into_clip(clip_path, srt_path, output_path, style_config)
            if final:
                final_paths.append(final.replace("\\", "/"))
        return final_paths
    except Exception:
        return final_paths
