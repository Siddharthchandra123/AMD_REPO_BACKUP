import base64,httpx
from app.config import settings

async def transcribe(audio,filename,content_type):
    async with httpx.AsyncClient(timeout=180) as c:
        r=await c.post(settings.asr_provider_url+"/transcribe",
            files={"file":(filename,audio,content_type)})
        r.raise_for_status(); return r.json()["text"]

async def synthesize(text):
    async with httpx.AsyncClient(timeout=180) as c:
        r=await c.post(settings.tts_provider_url+"/synthesize",json={"text":text})
        r.raise_for_status(); return r.json()
