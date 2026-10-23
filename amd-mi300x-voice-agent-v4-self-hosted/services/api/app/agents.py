from app.llm import llm

class Router:
    def route(self,text):
        t=text.lower()
        return {"rag":any(x in t for x in ["document","policy","manual","knowledge"]),
                "tools":any(x in t for x in ["calculate","search","lookup"])}

class Orchestrator:
    def __init__(self): self.router=Router()
    async def stream(self,text,history,context=None):
        route=self.router.route(text)
        system="You are a natural real-time voice assistant. Be concise, accurate, and conversational."
        if context: system+="\nKnowledge context:\n"+context
        messages=[{"role":"system","content":system}]+history+[{"role":"user","content":text}]
        async for token in llm.stream(messages): yield route,token
orchestrator=Orchestrator()
