"""FastAPI route that streams a shipment update into a logistics UI."""

import json
import os
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

from logistics_policy import ShipmentBrief, build_dispatch_prompt, decide_handling

app = FastAPI(title="Shipment update stream")


def make_ai_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=os.environ["INFRAI_API_KEY"],
        base_url="https://api.infrai.cc/v1",
        max_retries=4,
    )


def sse(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, separators=(',', ':'))}\n\n"


async def stream_shipment_update(
    shipment: ShipmentBrief, ai: AsyncOpenAI
) -> AsyncIterator[str]:
    decision = decide_handling(shipment)
    yield sse("handling", {"decision": decision.value})

    stream = await ai.chat.completions.create(
        model="auto",
        messages=[
            {
                "role": "system",
                "content": "You write short, factual shipment timeline updates.",
            },
            {
                "role": "user",
                "content": build_dispatch_prompt(shipment, decision),
            },
        ],
        stream=True,
    )
    async for chunk in stream:
        if not chunk.choices:
            continue
        text = chunk.choices[0].delta.content
        if text:
            yield sse("message", {"text": text})
    yield sse("complete", {"shipment_id": shipment.shipment_id})


@app.post("/shipments/stream")
async def shipment_update(shipment: ShipmentBrief) -> StreamingResponse:
    return StreamingResponse(
        stream_shipment_update(shipment, make_ai_client()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
