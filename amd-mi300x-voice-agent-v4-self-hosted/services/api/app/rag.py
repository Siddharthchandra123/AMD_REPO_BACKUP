from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance,VectorParams,PointStruct
from app.config import settings
import hashlib,math

client=AsyncQdrantClient(url=settings.qdrant_url)

def embed(text):
    # Deterministic placeholder embedding. Replace with a real embedding model service in production.
    h=hashlib.sha256(text.encode()).digest()
    vals=[h[i%len(h)]/255 for i in range(settings.embedding_dim)]
    norm=math.sqrt(sum(v*v for v in vals)) or 1
    return [v/norm for v in vals]

async def ensure():
    try:
        await client.get_collection(settings.qdrant_collection)
    except Exception:
        await client.create_collection(settings.qdrant_collection,
            vectors_config=VectorParams(size=settings.embedding_dim,distance=Distance.COSINE))

async def ingest(text,source):
    await ensure()
    pid=int(hashlib.md5((source+text).encode()).hexdigest()[:12],16)
    await client.upsert(settings.qdrant_collection,[PointStruct(id=pid,vector=embed(text),payload={"text":text,"source":source})])
    return pid

async def retrieve(query,limit=3):
    await ensure()
    hits=await client.query_points(settings.qdrant_collection,query=embed(query),limit=limit)
    return "\n".join(h.payload.get("text","") for h in hits.points)
