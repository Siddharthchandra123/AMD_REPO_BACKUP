import asyncio,json
from fastapi import FastAPI,WebSocket,WebSocketDisconnect,UploadFile,File
from fastapi.responses import Response
from pydantic import BaseModel
from prometheus_client import Counter,generate_latest,CONTENT_TYPE_LATEST
from app.session import store
from app.agents import orchestrator
from app.chunker import SentenceChunker
from app.services import transcribe,synthesize
from app.rag import ingest,retrieve

app=FastAPI(title="AMD MI300X Real-Time Voice Agent")
REQUESTS=Counter("voice_agent_requests_total","Total requests")

class Chat(BaseModel): text:str; session_id:str="default"
class Document(BaseModel): text:str; source:str="manual"

@app.get("/health")
async def health(): return {"status":"healthy","target":"AMD Instinct MI300X"}

@app.get("/ready")
async def ready(): return {"status":"ready"}

@app.get("/metrics")
async def metrics(): return Response(generate_latest(),media_type=CONTENT_TYPE_LATEST)

@app.post("/documents")
async def documents(d:Document):
    return {"id":await ingest(d.text,d.source)}

@app.post("/chat")
async def chat(body:Chat):
    REQUESTS.inc(); s=store.get(body.session_id); store.reset_cancel(body.session_id)
    ctx=await retrieve(body.text)
    out=""
    async for _,t in orchestrator.stream(body.text,s.history,ctx): out+=t
    s.history=(s.history+[{"role":"user","content":body.text},{"role":"assistant","content":out}])[-20:]
    return {"answer":out}



class TTSRequest(BaseModel):
    text: str

@app.post("/tts")
async def text_to_speech(body: TTSRequest):
    if not body.text.strip():
        return {"error": "Text cannot be empty"}

    return await synthesize(body.text)

@app.post("/voice")
async def voice(file:UploadFile=File(...)):
    audio=await file.read()
    text=await transcribe(audio,file.filename or "audio.webm",file.content_type or "audio/webm")
    answer=(await chat(Chat(text=text)))["answer"]
    speech=await synthesize(answer)
    return {"transcript":text,"answer":answer,**speech}

@app.websocket("/ws/realtime/{session_id}")
async def realtime(ws:WebSocket,session_id:str):
    await ws.accept(); s=store.get(session_id)
    try:
        while True:
            msg=await ws.receive_json()
            if msg.get("type")=="interrupt":
                store.cancel(session_id); await ws.send_json({"type":"interrupted"}); continue
            if msg.get("type")!="text": continue
            store.reset_cancel(session_id); text=msg["text"]; ctx=await retrieve(text)
            chunker=SentenceChunker(); full=""
            async for _,token in orchestrator.stream(text,s.history,ctx):
                if s.cancel_event.is_set(): break
                full+=token; await ws.send_json({"type":"token","text":token})
                for sentence in chunker.push(token):
                    if not s.cancel_event.is_set():
                        audio=await synthesize(sentence)
                        await ws.send_json({"type":"audio","text":sentence,**audio})
            for sentence in chunker.flush():
                if not s.cancel_event.is_set():
                    audio=await synthesize(sentence)
                    await ws.send_json({"type":"audio","text":sentence,**audio})
            if not s.cancel_event.is_set():
                s.history=(s.history+[{"role":"user","content":text},{"role":"assistant","content":full}])[-20:]
                await ws.send_json({"type":"done"})
    except WebSocketDisconnect: pass
