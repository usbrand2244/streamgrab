# app.py
import asyncio
import os
from flask import Flask, jsonify, request
from playwright.async_api import async_playwright

app = Flask(__name__)

# VidSrc embed URL pattern for movies
VIDSRC_MOVIE_URL = "https://vidsrc.to/embed/movie/{}"


async def extract_m3u8(imdb_id: str):
    """
    Opens the VidSrc embed page with a headless browser and
    intercepts network responses to find .m3u8 URLs.
    """
    found_urls = []
    embed_url = VIDSRC_MOVIE_URL.format(imdb_id)

    async with async_playwright() as p:
        # Launch Chromium in headless mode
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        page = await browser.new_page()

        # Listener: capture every network response
        async def handle_response(response):
            url = response.url
            if ".m3u8" in url and url not in found_urls:
                found_urls.append(url)

        page.on("response", handle_response)

        try:
            # Navigate and wait for the player to load
            await page.goto(embed_url, wait_until="networkidle", timeout=30000)
            # Give the player extra time to fire the m3u8 request
            await asyncio.sleep(5)
        except Exception as e:
            await browser.close()
            return {"success": False, "error": str(e), "urls": []}

        await browser.close()

    if found_urls:
        return {"success": True, "urls": found_urls, "embed_url": embed_url}
    else:
        return {
            "success": False,
            "error": "No .m3u8 URL found. The player may be protected or the ID is invalid.",
            "embed_url": embed_url,
            "urls": [],
        }


# ---------- Flask Routes ----------

@app.route("/stream/<imdb_id>", methods=["GET"])
def stream(imdb_id):
    """
    Endpoint: GET /stream/tt0111161
    Returns JSON with the extracted .m3u8 URLs.
    """
    result = asyncio.run(extract_m3u8(imdb_id))
    return jsonify(result)


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "service": "IMDb to M3U8 Resolver",
        "usage": "GET /stream/<imdb_id>",
        "example": "/stream/tt0111161"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
