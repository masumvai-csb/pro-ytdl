from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import time
import re
import json
from pytube import YouTube
from pytube.exceptions import PytubeError, VideoUnavailable, AgeRestrictedError
import urllib.parse

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
    """Extract YouTube video ID from various URL formats"""
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

def sanitize_filename(filename: str) -> str:
    """Remove invalid characters from filename"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename[:100]

@app.get("/", include_in_schema=False)
async def root():
    """Redirect to docs"""
    return RedirectResponse(url="/docs")

@app.get("/api")
async def api_root():
    """API Information"""
    return {
        "api_name": "YouTube Downloader API",
        "version": "2.0.0",
        "developer": "@YourName",
        "channel": "@YourChannel",
        "endpoints": {
            "/api/yt": "Download video/audio with direct links",
            "/api/info": "Get video information only",
            "/api/formats": "Get all available formats",
            "/api/audio": "Get audio only",
            "/api/video": "Get video only"
        },
        "usage": "GET /api/yt?url=YOUTUBE_URL&type=video|audio&quality=quality",
        "example": "https://your-api.vercel.app/api/yt?url=https://youtu.be/dQw4w9WgXcQ"
    }

@app.get("/api/yt")
async def download_youtube(
    url: str = Query(..., description="YouTube URL or Video ID"),
    type: str = Query("both", description="Type: video, audio, or both"),
    quality: Optional[str] = Query(None, description="Quality (e.g., 720p, 480p, 360p, highest, lowest)"),
    download: bool = Query(False, description="Redirect to download URL")
):
    """
    Main endpoint for downloading YouTube videos/audio
    Returns direct download links
    """
    start_time = time.time()
    
    try:
        # Extract video ID
        video_id = extract_video_id(url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL. Please provide a valid YouTube URL or Video ID")
        
        # Construct full URL
        full_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Create YouTube object
        yt = YouTube(full_url)
        
        # Get video title and sanitize it
        title = yt.title
        safe_title = sanitize_filename(title)
        
        # Calculate processing time
        processing_time = round(time.time() - start_time, 4)
        
        # Prepare base response
        response = {
            "success": True,
            "api_dev": "@YourName",
            "api_channel": "@YourChannel",
            "time_s": processing_time,
            "title": title,
            "video_id": video_id,
            "thumbnail": yt.thumbnail_url,
            "duration": yt.length,
            "author": yt.author,
            "views": yt.views,
            "publish_date": str(yt.publish_date) if yt.publish_date else None,
            "keywords": yt.keywords,
            "description": yt.description[:300] + "..." if len(yt.description) > 300 else yt.description,
            "data": {}
        }
        
        # Get all streams
        streams = yt.streams
        
        # Handle based on type parameter
        if type.lower() in ["video", "both"]:
            # Get video streams
            video_streams = streams.filter(progressive=True, file_extension='mp4')
            
            if quality:
                if quality == "highest":
                    video_stream = video_streams.get_highest_resolution()
                elif quality == "lowest":
                    video_stream = video_streams.get_lowest_resolution()
                else:
                    # Try to find specific quality
                    video_stream = video_streams.filter(res=quality).first()
                    if not video_stream:
                        # If progressive not found, try adaptive
                        video_stream = streams.filter(res=quality, file_extension='mp4').first()
            else:
                # Default: highest quality progressive
                video_stream = video_streams.get_highest_resolution()
            
            if video_stream:
                video_info = {
                    "url": video_stream.url,
                    "quality": video_stream.resolution,
                    "filesize": video_stream.filesize,
                    "filesize_mb": round(video_stream.filesize / (1024 * 1024), 2) if video_stream.filesize else None,
                    "mime_type": video_stream.mime_type,
                    "type": "progressive" if video_stream.is_progressive else "adaptive",
                    "fps": video_stream.fps,
                    "download_filename": f"{safe_title}_{video_stream.resolution}.mp4"
                }
                
                # If download parameter is True, redirect to video URL
                if download and type.lower() == "video":
                    return RedirectResponse(url=video_stream.url)
                
                response["data"]["video"] = video_info
        
        if type.lower() in ["audio", "both"]:
            # Get audio streams
            audio_streams = streams.filter(only_audio=True, file_extension='mp4')
            
            if quality and quality in ["highest", "lowest"]:
                # For audio, sort by bitrate
                sorted_audio = sorted(audio_streams, key=lambda x: x.bitrate or 0, reverse=(quality == "highest"))
                audio_stream = sorted_audio[0] if sorted_audio else None
            else:
                # Default: highest quality audio
                audio_stream = audio_streams.order_by('abr').desc().first()
            
            if audio_stream:
                audio_info = {
                    "url": audio_stream.url,
                    "bitrate": audio_stream.abr,
                    "filesize": audio_stream.filesize,
                    "filesize_mb": round(audio_stream.filesize / (1024 * 1024), 2) if audio_stream.filesize else None,
                    "mime_type": audio_stream.mime_type,
                    "download_filename": f"{safe_title}_audio.mp3"
                }
                
                # If download parameter is True, redirect to audio URL
                if download and type.lower() == "audio":
                    return RedirectResponse(url=audio_stream.url)
                
                response["data"]["audio"] = audio_info
        
        # If no streams found, provide available formats
        if not response["data"]:
            available_formats = []
            for stream in streams:
                format_info = {
                    "itag": stream.itag,
                    "mime_type": stream.mime_type,
                    "resolution": stream.resolution,
                    "fps": stream.fps,
                    "bitrate": stream.bitrate,
                    "type": "video+audio" if stream.is_progressive else "video" if stream.includes_video_track else "audio"
                }
                available_formats.append(format_info)
            
            response["available_formats"] = available_formats
            response["note"] = "No direct stream found for requested quality. Check available formats."
        
        return JSONResponse(content=response)
    
    except AgeRestrictedError:
        raise HTTPException(status_code=403, detail="This video is age restricted and cannot be downloaded")
    except VideoUnavailable:
        raise HTTPException(status_code=404, detail="Video is unavailable or private")
    except PytubeError as e:
        raise HTTPException(status_code=500, detail=f"YouTube API error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/api/info")
async def video_info(url: str = Query(..., description="YouTube URL or Video ID")):
    """Get video information without download links"""
    start_time = time.time()
    
    try:
        video_id = extract_video_id(url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        
        full_url = f"https://www.youtube.com/watch?v={video_id}"
        yt = YouTube(full_url)
        
        # Get captions
        captions = {}
        try:
            caption_tracks = yt.caption_tracks
            for track in caption_tracks:
                captions[track.code] = {
                    "name": track.name,
                    "language": track.name,
                    "code": track.code,
                    "url": f"/api/caption/{video_id}?lang={track.code}"
                }
        except:
            captions = {}
        
        response = {
            "success": True,
            "time_s": round(time.time() - start_time, 4),
            "video_id": video_id,
            "title": yt.title,
            "duration_seconds": yt.length,
            "duration_formatted": f"{yt.length // 60}:{yt.length % 60:02d}",
            "author": yt.author,
            "channel_url": yt.channel_url,
            "views": yt.views,
            "publish_date": str(yt.publish_date) if yt.publish_date else None,
            "description": yt.description,
            "keywords": yt.keywords,
            "thumbnail": yt.thumbnail_url,
            "age_restricted": yt.age_restricted,
            "captions": captions,
            "metadata": {
                "video_id": video_id,
                "url": full_url,
                "embed_url": f"https://www.youtube.com/embed/{video_id}"
            }
        }
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/audio")
async def audio_only(
    url: str = Query(..., description="YouTube URL or Video ID"),
    download: bool = Query(False, description="Redirect to audio download URL")
):
    """Get audio download link only"""
    response = await download_youtube(url=url, type="audio", download=download)
    return response

@app.get("/api/video")
async def video_only(
    url: str = Query(..., description="YouTube URL or Video ID"),
    quality: Optional[str] = Query("highest", description="Video quality"),
    download: bool = Query(False, description="Redirect to video download URL")
):
    """Get video download link only"""
    response = await download_youtube(url=url, type="video", quality=quality, download=download)
    return response

@app.get("/api/formats")
async def all_formats(url: str = Query(..., description="YouTube URL or Video ID")):
    """Get all available formats for a video"""
    start_time = time.time()
    
    try:
        video_id = extract_video_id(url)
        if not video_id:
            raise HTTPException(status_code=400, detail="Invalid YouTube URL")
        
        full_url = f"https://www.youtube.com/watch?v={video_id}"
        yt = YouTube(full_url)
        
        # Get all streams
        all_streams = yt.streams
        
        # Categorize streams
        progressive = []
        video_only = []
        audio_only = []
        
        for stream in all_streams:
            stream_info = {
                "itag": stream.itag,
                "mime_type": stream.mime_type,
                "resolution": stream.resolution,
                "fps": stream.fps,
                "bitrate": stream.bitrate,
                "filesize": stream.filesize,
                "filesize_mb": round(stream.filesize / (1024 * 1024), 2) if stream.filesize else None,
                "type": None,
                "url": stream.url,
                "codecs": {
                    "video": stream.video_codec,
                    "audio": stream.audio_codec
                }
            }
            
            if stream.is_progressive:
                stream_info["type"] = "progressive"
                progressive.append(stream_info)
            elif stream.includes_video_track and not stream.includes_audio_track:
                stream_info["type"] = "video_only"
                video_only.append(stream_info)
            elif stream.includes_audio_track and not stream.includes_video_track:
                stream_info["type"] = "audio_only"
                audio_only.append(stream_info)
        
        response = {
            "success": True,
            "time_s": round(time.time() - start_time, 4),
            "video_id": video_id,
            "title": yt.title,
            "total_streams": len(all_streams),
            "formats": {
                "progressive": sorted(progressive, key=lambda x: int(x["resolution"].replace('p', '')) if x["resolution"] else 0, reverse=True),
                "video_only": sorted(video_only, key=lambda x: int(x["resolution"].replace('p', '')) if x["resolution"] else 0, reverse=True),
                "audio_only": sorted(audio_only, key=lambda x: x["bitrate"] or 0, reverse=True)
            },
            "recommended": {
                "best_video": progressive[0] if progressive else None,
                "best_audio": audio_only[0] if audio_only else None,
                "smallest_size": min(all_streams, key=lambda x: x.filesize or float('inf')).itag if all_streams else None
            }
        }
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "YouTube Downloader API",
        "version": "2.0.0"
    }

@app.get("/api/search")
async def search_videos(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, description="Number of results", ge=1, le=50)
):
    """Search YouTube videos (Note: Requires YouTube Data API v3 key for full functionality)"""
    # This is a placeholder - you'll need YouTube Data API v3 key
    return {
        "note": "YouTube search requires API key. Use YouTube Data API v3.",
        "query": query,
        "limit": limit,
        "implement": "Add your YouTube Data API v3 key"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
