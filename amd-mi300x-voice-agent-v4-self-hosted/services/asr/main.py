import os,tempfile
from fastapi import FastAPI,UploadFile,File
import whisper
app=FastAPI()
model=whisper.load_model(os.getenv("WHISPER_MODEL","small"))
@app.get("/health")
def health(): return {"ok":True}
@app.post("/transcribe")
async def transcribe(file:UploadFile=File(...)):
    suffix=os.path.splitext(file.filename or ".webm")[1]
    with tempfile.NamedTemporaryFile(delete=False,suffix=suffix) as f:
        f.write(await file.read()); path=f.name
    try:
        return {"text":model.transcribe(path)["text"].strip()}
    finally:
        if os.path.exists(path): os.unlink(path)
