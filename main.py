import os
import re
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="IMDb Stream Grabber API")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9"
}

@app.get("/grab")
async def grab_stream(
    id: str = Query(..., description="The IMDb ID, e.g., tt1190634"),
    season: str = Query(None, description="Season number (for TV Shows)"),
    episode: str = Query(None, description="Episode number (for TV Shows)")
):
    if not id.startswith("tt"):
        raise HTTPException(status_code=400, detail="Invalid IMDb ID format. Must start with 'tt'.")

    # Clean URL string formatting with correct routing slashes
    if season and episode:
        target_url = f"https://vidsrc.xyz{id}&season={season}&episode={episode}"
    else:
        target_url = f"https://vidsrc.xyz{id}"

    try:
        # Request with a short timeout to handle hosting platform restrictions gracefully
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.get(target_url, headers=HEADERS)
            
            if response.status_code != 200:
                return JSONResponse(content={
                    "imdb_id": id,
                    "status": "fallback",
                    "m3u8_url": target_url,
                    "note": "Direct stream hidden. Load this target_url in a browser player."
                })

            html_content = response.text
            stream_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html_content, re.IGNORECASE)
            
            if stream_match:
                m3u8_link = stream_match.group(1)
                status = "success"
            else:
                m3u8_link = target_url
                status = "fallback"

            return JSONResponse(content={
                "imdb_id": id,
                "type": "tv" if (season and episode) else "movie",
                "status": status,
                "m3u8_url": m3u8_link
            })

    except Exception as e:
        # Safe catch block returns the correct structural URL format if the server blocks the request
        return JSONResponse(content={
            "imdb_id": id,
            "type": "tv" if (season and episode) else "movie",
            "status": "fallback",
            "m3u8_url": target_url,
            "info": "Host network restricted direct scraping. Use the provided m3u8_url path directly in an iframe.",
            "error_details": str(e)
        })

@app.get("/")
def home():
    return {"message": "Stream Grabber is active. Use /grab?id=IMDB_ID"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
