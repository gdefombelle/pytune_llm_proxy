from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
import hashlib
import json
import asyncio

from pytune_llm.llm_connector import call_llm
from redis.asyncio import Redis

router = APIRouter()
redis = Redis(host="localhost", port=6379, decode_responses=True)


class CompletionRequest(BaseModel):
    prompt: str
    context: Optional[dict] = {}
    metadata: Optional[dict] = {}  # Peut contenir "llm_model", "llm_backend", etc.
    cache: Optional[bool] = True   # Active ou non la mise en cache


def make_cache_key(prompt: str, context: dict, metadata: dict) -> str:
    raw = json.dumps({"prompt": prompt, "context": context, "metadata": metadata}, sort_keys=True)
    return "llmcache:" + hashlib.sha256(raw.encode()).hexdigest()


@router.post("/llm/completion")
async def llm_completion(req: CompletionRequest):
    key = make_cache_key(req.prompt, req.context or {}, req.metadata or {})

    # 🔄 Cache Redis
    if req.cache:
        cached = await redis.get(key)
        if cached:
            return {"result": cached, "cached": True}

    try:
        response = await call_llm(req.prompt, req.context or {}, req.metadata or {})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM call failed: {str(e)}")

    if req.cache:
        await redis.setex(key, 86400, response)

    return {"result": response, "cached": False}
