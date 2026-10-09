import os
import uuid
import mimetypes
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import yt_dlp
from dotenv import load_dotenv

app = FastAPI()

# Load environment variables from .env file
load_dotenv()

# CORS configuration
allowed_origin = os.getenv("ALLOWED_ORIGIN", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[allowed_origin] if allowed_origin != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/download")
async def download_video(url: str = Query(...), format: str = Query("best")):
    try:
        uid = uuid.uuid4().hex[:8]
        output_template = f"/tmp/{uid}.%(ext)s"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

        # Quick metadata check to get title and extension
        with yt_dlp.YoutubeDL({
            "quiet": True,
            "skip_download": True,
            "no_warnings": True,
            "http_headers": headers,
        }) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "video").replace("/", "-").replace("\\", "-").replace(":", "-")
            extension = info.get("ext", "mp4")
            filename = f"{title}.{extension}"

        # Actual download
        ydl_opts = {
            "format": format,
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "merge_output_format": "mp4",
            "socket_timeout": 30,
            "http_headers": headers,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        actual_file_path = None
        for f in os.listdir("/tmp"):
            if f.startswith(uid):
                actual_file_path = os.path.join("/tmp", f)
                break

        if not actual_file_path or not os.path.exists(actual_file_path):
            raise HTTPException(status_code=500, detail="Download failed or file was not created.")

        mimetype, _ = mimetypes.guess_type(filename)
        if mimetype is None:
            mimetype = "application/octet-stream"

        def iterfile():
            with open(actual_file_path, "rb") as f:
                yield from f
            try:
                os.unlink(actual_file_path)
            except FileNotFoundError:
                pass

        return StreamingResponse(
            iterfile(),
            media_type=mimetype,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during download: {str(e)}")


@app.get("/")
async def root():
    return {
        "message": "Welcome to the Social Media Video Downloader API.",
        "usage": "/download?url=<video_url>&format=<video_format>",
        "example": "https://your-domain.com/download?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ&format=best"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
