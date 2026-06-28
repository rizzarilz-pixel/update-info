from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx
from google_play_scraper import app as play_scraper
from bs4 import BeautifulSoup
import re
import asyncio
import json
import os

app = FastAPI()

# Konfigurasi CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Bisa diganti dengan domain spesifik untuk keamanan
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

FF_MANIA_URL = "https://www.freefiremania.com.br/free-fire-new-update.html"
HEADERS = {'User-Agent': 'Mozilla/5.0'}

def load_client_urls():
    file_path = 'clients_url.json'
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return {"error": "clients_url.json not found"}

async def get_api_update():
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: play_scraper('com.dts.freefireth', lang="bn", country='id'))
        play_version = result['version']
        
        api_url = f'https://version.ggwhitehawk.com/live/ver.php?version={play_version}&lang=bn&device=android&channel=android&appstore=googleplay&region=ID&whitelist_version=1.3.0&whitelist_sp_version=1.0.0'
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(api_url)
            data = response.json()

        return {
            "remote_version": data.get('remote_version'),
            "server_url": data.get('server_url'),
            "latest_release_version": data.get('latest_release_version'),
            "play_store_version": play_version
        }
    except Exception as e:
        return {"error": str(e)}

async def get_scraping_update():
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=HEADERS) as client:
            r = await client.get(FF_MANIA_URL)
            r.raise_for_status()
        
        s = BeautifulSoup(r.content, 'html.parser')
        t = ' '.join(s.get_text().split())
        p = r'The next Free Fire update happens on (.+?) \((GMT[^)]+)\), remaining (.+?)\.'
        m = re.search(p, t, re.IGNORECASE)
        
        v = re.findall(r'OB\d+', t)
        uv = list(dict.fromkeys(v))
        
        if m:
            return {
                "NextUpdate_Date": f"{m.group(1).strip()} ({m.group(2).strip()})",
                "countdown": m.group(3).strip(),
                "from_version": uv[0] if len(uv) > 0 else "N/A",
                "to_version": uv[1] if len(uv) > 1 else "N/A"
            }
        return {"error": "Scraping pattern not found"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/update")
async def get_combined_update():
    region_urls = load_client_urls()
    api_task, web_task = await asyncio.gather(get_api_update(), get_scraping_update())

    return {
        "status": "success",
        "SourceUpdate_info": api_task,
        "GameUpdate_info": web_task,
        "Region_URLs": region_urls,
        "Credit": "CGU TEAM",
    }

# Endpoint tambahan untuk health check
@app.get("/")
async def root():
    return {"message": "Free Fire Update API is running", "status": "online"}
