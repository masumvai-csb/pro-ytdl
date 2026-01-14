from fastapi import FastAPI, Query
import time
import re

app = FastAPI()

def extract_video_id(url: str):
    patterns = [
        r'(?:youtu\.be/|youtube\.com/watch\?v=)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

@app.get("/api/yt")
async def yt_download(url: str = Query(...)):
    video_id = extract_video_id(url)
    
    if not video_id:
        return {"error": "Invalid URL"}
    
    # Simple response without pytube
    return {
        "api_dev": "@masumvai",
        "api_channel": "@Masum_Tech_Sensei",
        "time_s": 1.5,
        "title": f"Video {video_id}",
        "video_id": video_id,
        "data": {
            "video": f"https://dl.ymcdn.org/04caafe31b0869a0601e4912f5170a6d/{video_id}",
            "audio": f"https://dl.ymcdn.org/8ce857f5628c8c6d3fdde2a01f30e01b/{video_id}"
        },
        "note": "This is a demo response. For real download, use external services.",
        "external_services": [
            f"https://yt1s.com/youtube-to-mp4/{video_id}",
            f"https://ssyoutube.com/watch?v={video_id}",
            f"https://yt5s.com/en/?q=https://youtube.com/watch?v={video_id}"
        ]
    }

@app.get("/")
async def root():
    return {"message": "YouTube API Working"}
