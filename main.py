import os
import re
import httpx
import uvicorn
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="VidCore Stream Grabber")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Referer": "https://vidcore.org/"
}

@app.get("/grab")
async def grab_stream(
    id: str = Query(..., description="The TMDB ID"),
    season: str = Query(None, description="Season number"),
    episode: str = Query(None, description="Episode number")
):
    if season and episode:
        target_url = f"https://vidcore.org/embed/tv/{id}/{season}/{episode}"
    else:
        target_url = f"https://vidcore.org/embed/movie/{id}"

    try:
        async with httpx.AsyncClient(timeout=4.0, follow_redirects=True) as client:
            response = await client.get(target_url, headers=HEADERS)
            html_content = response.text
            
            # Scans the rendered source configuration blocks for raw .m3u8 files
            m3u8_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html_content, re.IGNORECASE)
            
            if m3u8_match:
                return JSONResponse(content={
                    "tmdb_id": id,
                    "status": "success",
                    "stream_type": "direct_m3u8",
                    "url": m3u8_match.group(1)
                })
                
    except Exception:
        pass

    # If the file is encrypted on the server side, return the active endpoint player 
    return JSONResponse(content={
        "tmdb_id": id,
        "status": "fallback",
        "stream_type": "player_url",
        "url": target_url,
        "note": "The .m3u8 manifest is dynamically tokens-signed. Open this URL to play or inspect the stream."
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
