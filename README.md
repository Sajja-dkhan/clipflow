# ClipFlow

ClipFlow is a localhost Flask app that monitors a YouTube channel, downloads the newest video, extracts clips, generates AI captions, and serves downloadable final clips.

## 1. Prerequisites
- Python 3.10+
- FFmpeg installed
- Git

## 2. Installation
```bash
git clone [repo]
cd clipflow
pip install -r requirements.txt
```

## 3. FFmpeg Setup
- **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html), then add FFmpeg to PATH.
- **Mac:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg`

## 4. Environment Setup
```bash
cp .env.example .env
```
Optionally set `YOUTUBE_API_KEY` (free key from `console.cloud.google.com`).

## 5. Run the app
```bash
python app.py
```
Open browser: `http://localhost:5000`

## 6. First Use
1. Go to **Channel Setup** and paste your YouTube channel URL.
2. Click **Save & Verify Channel**.
3. Click **Check Now** on Dashboard.
4. Wait for processing (5-15 minutes depending on video length).
5. Open **My Clips** to preview/download captioned clips.
