import os
import re
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

app = FastAPI(title="IMDb Stream Grabber API")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://vidsrc.to"
}

@app.get("/grab")
async def grab_stream(
    id: str = Query(..., description="The IMDb ID, e.g., tt1190634"),
    season: str = Query(None, description="Season number (for TV Shows)"),
    episode: str = Query(None, description="Episode number (for TV Shows)")
):
    if not id.startswith("tt"):
        raise HTTPException(status_code=400, detail="Invalid IMDb ID format. Must start with 'tt'.")

if season and episode:
    target_url = f"https://vidsrc.cc{id}/{season}/{episode}"
else:
    target_url = f"https://vidsrc.cc{id}"


    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.get(target_url, headers=HEADERS)
            
            if response.status_code != 200:
                raise HTTPException(status_code=502, detail="Failed to fetch data from the provider.")

            html_content = response.text
            stream_match = re.search(r'(https?://[^\s"\']+\.m3u8[^\s"\']*)', html_content, re.IGNORECASE)
            
            if stream_match:
                m3u8_link = stream_match.group(1)
            else:
                m3u8_link = f"https://vidsrc.toembed/movie/{id}" 

            return JSONResponse(content={
                "imdb_id": id,
                "type": "tv" if (season and episode) else "movie",
                "status": "success",
                "m3u8_url": m3u8_link
            })

    except httpx.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Network error: {str(e)}")

@app.get("/")
def home():
    return {"message": "Stream Grabber is active on Render. Use /grab?id=IMDB_ID"}

# This block allows Render to assign the required dynamic port automatically
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
