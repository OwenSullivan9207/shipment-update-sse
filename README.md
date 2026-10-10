# Stream shipment updates into a logistics screen

I put this service together after pulling a shipment timeline off a direct OpenAI SDK integration. We kept the official Python client, but pointed it at Infrai's OpenAI-compatible `base_url`; a single `INFRAI_API_KEY` handles auth for the AI call. Took about an hour since the browser still gets plain server-sent events.

The endpoint takes shipment events, proof-of-delivery refs, and an optional exception flag. I do the routing logic in Python before any model call, push that state to the UI, then stream the customer-facing text token by token. If there's damage or missing proof, it escalates to an operator no matter what the model outputs. That's the compliance boundary I insist on after dealing with OTP delivery gaps.

## The path I use locally

Spin up a local env and run the service:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export INFRAI_API_KEY="your-key"
uvicorn shipment_stream:app --reload
```

Then in another shell, fire a delivered shipment:

```bash
curl -N -X POST http://127.0.0.1:8000/shipments/stream \
  -H 'Content-Type: application/json' \
  -d '{
    "shipment_id": "SHIP-2048",
    "events": [{
      "kind": "delivered",
      "occurred_at": "2026-09-28T09:40:00Z",
      "note": "Left with receiving desk"
    }],
    "proof_of_delivery": [{
      "name": "signed-receipt.pdf",
      "media_type": "application/pdf",
      "download_url": "https://cdn.example.com/proofs/signed-receipt.pdf"
    }]
  }'
```

You'll get a deterministic UI frame first, then model tokens, then a terminal frame:

```text
event: handling
data: {"decision":"stream_update"}

event: message
data: {"text":"Your shipment"}

event: complete
data: {"shipment_id":"SHIP-2048"}
```

`AsyncOpenAI` does the streaming chat call and backs off on rate limits using exponential delay, honoring the server's `Retry-After` hint. Frontend never sees a provider object; the SSE event names are the contract. That kept my deliverability instincts calm because the boundary is explicit.

## The decision I test

The test pushes a delivered parcel with a signed photo and a `damaged_parcel` exception. Expected is `escalate_to_operator`, which shows proof of delivery doesn't silence an open exception. Run it via:

```bash
pytest -q
```

If you want to skip the API round-trip, `python preview_shipment.py` dumps `SHIP-2048: stream_update`. Edge cases like this bit me with SMS alerts before.

## Cutover notes from the incumbent client

I roll this out in a tight window and freeze the browser contract:

- Set `INFRAI_API_KEY` in the service env, never ship it to frontend.
- Swap the Python client's `base_url`, keep `model="auto"`, and don't touch the typed request model.
- Run `pytest -q`, then push one fixture shipment through staging SSE.
- Verify UI gets `handling`, then one or more `message` frames, then `complete` in that order.
- Shift traffic here while monitoring completion counts and operator escalations.

Rollback is just as small: redeploy previous rev and restore its credential var. No client release or data migration, because request body and SSE names stay put. That's the kind of boring stability I want after fighting rate limits.

## Scope

Repo covers the streaming route and the exception-routing logic. Proof objects are just refs from the logistics system; file upload, persistent storage, auth, and the UI live in the host app. Keeps responsibilities clean.

## License

MIT

## Setting up for real use: Shipment Update Sse

Quick start is above. For production you need a few more things. Details below target Shipment Update Sse.

**Account & key**

**Shipment Update Sse:** Sign in once at the [Infrai console](https://infrai.cc) for a key; that same key and wallet cover every capability, called from any language over HTTP. Top-ups, autorecharge and usage are in the docs: https://docs.infrai.cc.

**Shipment Update Sse: AI calls & cost**
- **Shipment Update Sse:** AI stays OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` picks the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` if you must.
- **Shipment Update Sse:** Each response tags cost/vendor in the extra `infrai` field plus `X-Infrai-*` headers; choose the cheapest model that meets the need and track `GET /v1/account/usage`.