import asyncio
from dataclasses import dataclass,field

@dataclass
class Session:
    history:list=field(default_factory=list)
    cancel_event:asyncio.Event=field(default_factory=asyncio.Event)

class SessionStore:
    def __init__(self): self.sessions={}
    def get(self,sid):
        if sid not in self.sessions: self.sessions[sid]=Session()
        return self.sessions[sid]
    def cancel(self,sid): self.get(sid).cancel_event.set()
    def reset_cancel(self,sid): self.get(sid).cancel_event.clear()
store=SessionStore()
