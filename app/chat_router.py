from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional
import hashlib
import json
import zlib

from pytune_llm.llm_backends.openai_backend import call_openai_llm
from redis.asyncio import Redis
from pytune_configuration.redis_config import get_redis_client
from pytune_llm.llm_utils import compress_json, decompress_json, make_cache_key, serialize_messages

router = APIRouter()

class Message(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str

class ChatRequest(BaseModel):
    model: Optional[str] = "gpt-4o-mini"
    messages: List[Message]
    cache: Optional[bool] = True

@router.post("/llm/chat")
async def chat_completion(req: ChatRequest):
    messages = serialize_messages(req.messages)
    key = make_cache_key(messages, req.model)
    redis: Redis = await get_redis_client()

    if req.cache:
        cached = await redis.get(key)
        if cached:
            return {"result": decompress_json(cached), "cached": True}

    try:
        response = await call_openai_llm(
            messages=messages,
            model=req.model
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat call failed: {str(e)}")

    if req.cache:
        await redis.setex(key, 86400, compress_json(response))

    return {"result": response, "cached": False}
