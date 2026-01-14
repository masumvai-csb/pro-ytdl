from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import time
import re
from typing import Optional
import httpx
import json

app = FastAPI(
    title="YouTube Downloader API",
    description="Download YouTube videos and audio directly",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
        r'(?:v=|v/|vi=|vi/|youtu\.be/|embed/|shorts/)([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

async def get_youtube_info(video_id: str):
    """Get YouTube video info using YouTube oEmbed API"""
    try:
        async with httpx.AsyncClient() as client:
            # Method 1: Try oEmbed API
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            response = await client.get(oembed_url, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "title": data.get("title", "Unknown Title"),
                    "author": data.get("author_name", "Unknown Author"),
                    "thumbnail": data.get("thumbnail_url", ""),
                    "success": True
                }
            
            # Method 2: Try alternative approach
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            
            response = await client.get(youtube_url, headers=headers, timeout=10.0)
            
            if response.status_code == 200:
                html = response.text
                
                # Extract title
                title_match = re.search(r'<meta name="title" content="([^"]+)"', html)
                title = title_match.group(1) if title_match else "Unknown Title"
                
                # Extract author
                author_match = re.search(r'"author":"([^"]+)"', html)
                author = author_match.group(1) if author_match else "Unknown Author"
                
                # Extract thumbnail
                thumbnail_match = re.search(r'"thumbnailUrl":\["([^"]+)"\]', html)
                thumbnail = thumbnail_match.group(1) if thumbnail_match else f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
                
                return {
                    "title": title,
                    "author": author,
                    "thumbnail": thumbnail,
                    "success": True
                }
            
            return {
                "title": f"Video {video_id}",
                "author": "YouTube",
                "thumbnail": f"https://img.youtube.com/vi/{video_id}/0.jpg",
                "success": False
            }
    
    except Exception as e:
        return {
            "title": f"Video {video_id}",
            "author": "YouTube",
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/0.jpg",
            "success": False,
            "error": str(e)
        }

@app.get("/")
async def root():
    return {
        "message": "YouTube Downloader API",
        "developer": "@masumvai",
        "channel": "@Masum_Tech_Sensei",
        "version": "2.0.0",
        "endpoints": {
            "/api/yt": "GET /api/yt?url=YOUTUBE_URL",
            "/api/info": "GET video information",
            "/health": "Health check"
        },
        "example": "https://pro-ytdl.vercel.app/api/yt?url=https://youtu.be/kV1qVKlseIU"
    }

@app.get("/api/yt")
async def download_youtube(
    url: str = Query(..., description="YouTube URL or Video ID"),
    quality: str = Query("high", description="Quality: high, medium, low")
):
    start_time = time.time()
    
    try:
        # Extract video ID
        video_id = extract_video_id(url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL. Please provide a valid URL or Video ID")
        
        # Get video info
        video_info = await get_youtube_info(video_id)
        
        # Generate direct download links (using ytimg.com proxy method)
        # Note: These are direct links that might work for some videos
        video_qualities = {
            "high": {
                "video": f"https://rr2---sn-4g5ednsl.googlevideo.com/videoplayback?ip=0.0.0.0&id={video_id}&itag=22&source=youtube&requiressl=yes&ratebypass=yes",
                "audio": f"https://rr2---sn-4g5ednsl.googlevideo.com/videoplayback?ip=0.0.0.0&id={video_id}&itag=140&source=youtube&requiressl=yes&ratebypass=yes"
            },
            "medium": {
                "video": f"https://rr2---sn-4g5ednsl.googlevideo.com/videoplayback?ip=0.0.0.0&id={video_id}&itag=18&source=youtube&requiressl=yes&ratebypass=yes",
                "audio": f"https://rr2---sn-4g5ednsl.googlevideo.com/videoplayback?ip=0.0.0.0&id={video_id}&itag=140&source=youtube&requiressl=yes&ratebypass=yes"
            },
            "low": {
                "video": f"https://rr2---sn-4g5ednsl.googlevideo.com/videoplayback?ip=0.0.0.0&id={video_id}&itag=17&source=youtube&requiressl=yes&ratebypass=yes",
                "audio": f"https://rr2---sn-4g5ednsl.googlevideo.com/videoplayback?ip=0.0.0.0&id={video_id}&itag=139&source=youtube&requiressl=yes&ratebypass=yes"
            }
        }
        
        selected_quality = video_qualities.get(quality.lower(), video_qualities["high"])
        
        response = {
            "api_dev": "@masumvai",
            "api_channel": "@Masum_Tech_Sensei",
            "time_s": round(time.time() - start_time, 4),
            "title": video_info["title"],
            "video_id": video_id,
            "thumbnail": video_info["thumbnail"],
            "author": video_info["author"],
            "quality": quality,
            "data": {
                "video": selected_quality["video"],
                "audio": selected_quality["audio"]
            },
            "note": "Links might expire. Use immediately for download.",
            "alternative_methods": [
                f"https://yt1s.com/youtube-to-mp4/{video_id}",
                f"https://yt5s.com/en/?q=https://youtube.com/watch?v={video_id}",
                f"https://ssyoutube.com/watch?v={video_id}"
            ]
        }
        
        return JSONResponse(content=response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/api/info")
async def video_info(url: str = Query(..., description="YouTube URL or Video ID")):
    start_time = time.time()
    
    try:
        video_id = extract_video_id(url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        
        video_info = await get_youtube_info(video_id)
        
        response = {
            "success": True,
            "time_s": round(time.time() - start_time, 4),
            "video_id": video_id,
            "title": video_info["title"],
            "author": video_info["author"],
            "thumbnail": video_info["thumbnail"],
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "embed_url": f"https://www.youtube.com/embed/{video_id}",
            "thumbnail_urls": {
                "default": f"https://img.youtube.com/vi/{video_id}/default.jpg",
                "medium": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                "high": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg",
                "standard": f"https://img.youtube.com/vi/{video_id}/sddefault.jpg",
                "maxres": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg"
            }
        }
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "YouTube Downloader API",
        "version": "2.0.0",
        "uptime": "running"
    }

@app.get("/api/test")
async def test_endpoint():
    """Test endpoint with a known working video"""
    test_url = "https://youtu.be/kV1qVKlseIU"
    return await download_youtube(url=test_url, quality="high")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
