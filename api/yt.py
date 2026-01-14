from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import time
import re
from pytube import YouTube

router = APIRouter(prefix="/api", tags=["YouTube"])

def extract_video_id(url: str) -> Optional[str]:
    patterns = [
        r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

@router.get("/yt")
async def youtube_download(
    url: str = Query(..., description="YouTube URL"),
    type: str = Query("both", description="video, audio, or both")
):
    start_time = time.time()
    
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid URL")
    
    try:
        yt = YouTube(f"https://www.youtube.com/watch?v={video_id}")
        
        response = {
            "api_dev": "@YourName",
            "api_channel": "@YourChannel",
            "time_s": round(time.time() - start_time, 4),
            "title": yt.title,
            "video_id": video_id,
            "data": {}
        }
        
        streams = yt.streams
        
        if type in ["video", "both"]:
            video = streams.filter(progressive=True, file_extension='mp4').get_highest_resolution()
            if video:
                response["data"]["video"] = {
                    "url": video.url,
                    "quality": video.resolution,
                    "size_mb": round(video.filesize / (1024*1024), 2) if video.filesize else None
                }
        
        if type in ["audio", "both"]:
            audio = streams.filter(only_audio=True).first()
            if audio:
                response["data"]["audio"] = {
                    "url": audio.url,
                    "bitrate": audio.abr,
                    "size_mb": round(audio.filesize / (1024*1024), 2) if audio.filesize else None
                }
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
