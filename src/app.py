import asyncio
import json
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from src.classifier import classify
from src.memory import get_prior_user_turns, save_turn
from src.router import dispatch
from src.safety import check as check_safety
from src.schemas import ChatRequest


PIPELINE_TIMEOUT_SECONDS = 8

app = FastAPI(title="Valura AI Microservice")


def _sse(event: str, data: dict | str) -> str:
    if not isinstance(data, str):
        data = json.dumps(data, separators=(",", ":"))
    return f"event: {event}\ndata: {data}\n\n"


def _load_user_context(request: ChatRequest) -> dict:
    if request.user_context is not None:
        return request.user_context

    if request.user_id:
        fixtures_dir = Path(__file__).resolve().parent.parent / "fixtures" / "users"
        for path in fixtures_dir.glob("*.json"):
            with open(path, encoding="utf-8") as file:
                user = json.load(file)
            if user.get("user_id") == request.user_id:
                return user

    return {
        "user_id": request.user_id or "anonymous",
        "risk_profile": "moderate",
        "base_currency": "USD",
        "positions": [],
        "preferences": {"preferred_benchmark": "S&P 500"},
    }


def _chunk_text(text: str, size: int = 700) -> list[str]:
    return [text[index : index + size] for index in range(0, len(text), size)] or [""]


async def _run_pipeline(request: ChatRequest) -> list[tuple[str, dict | str]]:
    safety = check_safety(request.query)
    if safety.blocked:
        save_turn(request.session_id, "user", request.query)
        save_turn(request.session_id, "assistant", safety.message)
        return [
            (
                "metadata",
                {
                    "blocked": True,
                    "safety_category": safety.category,
                    "agent": None,
                },
            ),
            ("chunk", safety.message),
            ("done", {"status": "blocked"}),
        ]

    prior_turns = get_prior_user_turns(request.session_id)
    classification = classify(request.query, prior_user_turns=prior_turns)
    user_context = _load_user_context(request)
    response = dispatch(classification, user_context=user_context)

    save_turn(request.session_id, "user", request.query)
    save_turn(request.session_id, "assistant", json.dumps(response, separators=(",", ":")))

    body = json.dumps(response, separators=(",", ":"))
    events: list[tuple[str, dict | str]] = [
        (
            "metadata",
            {
                "blocked": False,
                "agent": classification.agent,
                "intent": classification.intent,
                "entities": classification.entities,
                "classifier_safety": classification.safety,
            },
        )
    ]
    events.extend(("chunk", chunk) for chunk in _chunk_text(body))
    events.append(("done", {"status": "ok"}))
    return events


async def _event_stream(request: ChatRequest) -> AsyncIterator[str]:
    try:
        events = await asyncio.wait_for(_run_pipeline(request), timeout=PIPELINE_TIMEOUT_SECONDS)
        for event, data in events:
            yield _sse(event, data)
            await asyncio.sleep(0)
    except asyncio.TimeoutError:
        yield _sse(
            "error",
            {
                "code": "pipeline_timeout",
                "message": f"Pipeline exceeded {PIPELINE_TIMEOUT_SECONDS} seconds.",
            },
        )
        yield _sse("done", {"status": "error"})
    except Exception:
        yield _sse(
            "error",
            {
                "code": "pipeline_error",
                "message": "The request could not be completed safely.",
            },
        )
        yield _sse("done", {"status": "error"})


@app.post("/v1/chat/stream")
async def chat_stream(request: ChatRequest):
    return StreamingResponse(_event_stream(request), media_type="text/event-stream")
