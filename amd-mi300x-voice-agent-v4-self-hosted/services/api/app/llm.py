import json,httpx
from app.config import settings

class LLM:
    async def stream(self,messages):
        payload={"model":settings.vllm_model,"messages":messages,"stream":True,"temperature":0.3}
        url=settings.vllm_base_url.rstrip("/")+"/chat/completions"
        async with httpx.AsyncClient(timeout=180) as c:
            async with c.stream("POST",url,json=payload) as r:
                r.raise_for_status()
                async for line in r.aiter_lines():
                    if not line.startswith("data: "): continue
                    data=line[6:]
                    if data=="[DONE]": break
                    try:
                        delta=json.loads(data)["choices"][0]["delta"].get("content","")
                        if delta: yield delta
                    except Exception: continue
llm=LLM()
