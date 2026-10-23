import re
class SentenceChunker:
    def __init__(self): self.buffer=""
    def push(self,text):
        self.buffer+=text
        parts=re.split(r'(?<=[.!?])\s+',self.buffer)
        if len(parts)<=1: return []
        self.buffer=parts.pop()
        return [p.strip() for p in parts if p.strip()]
    def flush(self):
        x=self.buffer.strip(); self.buffer=""; return [x] if x else []
