from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl
from typing import List, Optional
import hashlib
import json

from pytune_llm.llm_backends.openai_backend import call_openai_llm
from redis.asyncio import Redis

router = APIRouter()
redis = Redis(host="localhost", port=6379, decode_responses=True)


class VisionMessage(BaseModel):
    type: str  # "text" ou "image_url"
    text: Optional[str] = None
    image_url: Optional[dict] = None  # {"url": "https://..."}


class VisionRequest(BaseModel):
    model: Optional[str] = "gpt-4o"
    prompt: str
    image_urls: List[HttpUrl]
    cache: Optional[bool] = True


def make_cache_key(prompt: str, image_urls: List[str], model: str) -> str:
    raw = json.dumps({"model": model, "prompt": prompt, "images": image_urls}, sort_keys=True)
    return "llmcache:vision:" + hashlib.sha256(raw.encode()).hexdigest()


@router.post("/llm/vision")
async def vision_completion(req: VisionRequest):
    key = make_cache_key(req.prompt, req.image_urls, req.model)

    if req.cache:
        cached = await redis.get(key)
        if cached:
            return {"result": json.loads(cached), "cached": True}

    try:
        messages = [
            {"role": "system", "content": "You are an expert in image understanding."},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": req.prompt},
                    *[{"type": "image_url", "image_url": {"url": url}} for url in req.image_urls]
                ]
            }
        ]

        response = await call_openai_llm(messages=messages, model=req.model, vision=True)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision call failed: {str(e)}")

    if req.cache:
        await redis.setex(key, 86400, json.dumps(response))

    return {"result": response, "cached": False}