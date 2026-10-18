import os
import re
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="IMDb Stream Grabber API")

# Updated headers to emulate a secure browser session
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
    "Pragma": "no-cache"
}

@app.get("/grab")
async def grab_stream(
    id: str = Query(..., description="The IMDb ID, e.g., tt1190634"),
    season: str = Query(None, description="Season number (for TV Shows)"),
    episode: str = Query(None, description="Episode number (for TV Shows)")
):
    # Standard format validation
    if not id.startswith("tt"):
        raise HTTPException(status_code=400, detail="Invalid IMDb ID format. Must start with 'tt'.")

    # Using an active, structured provider path
    if season and episode:
        target_url = f"https://vidsrc.pm{id}/{season}/{episode}"
    else:
        target_url = f"https://vidsrc.pm{id}"

    try:
        # Using a strict 5-second timeout to prevent Railway/Render from hanging and crashing
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.get(target_url, headers=HEADERS)
            
            if response.status_code != 200:
                # Safe return if domain changes or blocks access
                return JSONResponse(content={
                    "imdb_id": id,
                    "status": "fallback",
                    "m3u8_url": target_url,
                    "note": "Direct stream hidden. Use target_url inside an iframe or web player."
                })

            html_content = response.text
            
            # Scrape for standard clear-text stream patterns
            stream_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html_content, re.IGNORECASE)
            
            if stream_match:
                m3u8_link = stream_match.group(1)
                status = "success"
            else:
                # If the stream source is tokenized/encrypted, provide the direct functional embed link
                m3u8_link = target_url
                status = "fallback"

            return JSONResponse(content={
                "imdb_id": id,
                "type": "tv" if (season and episode) else "movie",
                "status": status,
                "m3u8_url": m3u8_link
            })

    except Exception as e:
        # Fallback layer: If the scraper fails or times out, it gracefully returns the endpoint instead of crashing
        return JSONResponse(content={
            "imdb_id": id,
            "type": "tv" if (season and episode) else "movie",
            "status": "fallback",
            "m3u8_url": target_url,
            "error_log": str(e)
        })

@app.get("/")
def home():
    return {"message": "Stream Grabber is active. Use /grab?id=IMDB_ID"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
