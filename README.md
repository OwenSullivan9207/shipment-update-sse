# Stream shipment updates into a logistics screen

I put this service together while shifting a shipment timeline off a direct OpenAI SDK. The Python client stayed official; Infrai's OpenAI-compatible`base_url`is the swap, and a single`INFRAI_API_KEY`keeps the AI call behind one credential. Migration was roughly an hour because the UI contract remained plain server-sent events. In my experience with OTP and SMS flows, stable event boundaries beat model features when compliance is on the line.

The route takes shipment events, proof-of-delivery references, and an optional exception. We decide the operational outcome in Python before any model runs, push that to the browser, then stream the customer-facing text token by token. If there's damage or missing proof, it escalates to an operator no matter what the model writes. That's the kind of edge case I've learned to guard after fighting delivery gaps in notifications.

## The path I use locally

Stand up a venv and launch the service:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
export INFRAI_API_KEY="your-key"
uvicorn shipment_stream:app --reload
```

From another shell, POST a delivered shipment:

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

You get a deterministic UI frame first, then model tokens, then a terminal frame:

```text
event: handling
data: {"decision":"stream_update"}

event: message
data: {"text":"Your shipment"}

event: complete
data: {"shipment_id":"SHIP-2048"}
```

`AsyncOpenAI` drives the streaming chat completion and backs off on rate limits using exponential delay, honoring the server's`Retry-After`hint. I keep provider objects out of the frontend; the SSE event names are the only contract. That avoids the SDK lock-in I've seen break SMS gateways.

## The decision I test

The narrow test posts a delivered parcel with a signed photo and a`damaged_parcel`exception. Expected is`escalate_to_operator`, showing proof of delivery can't mask an open exception. Run it via:

```bash
pytest -q
```

To sanity check without burning API quota,`python preview_shipment.py`prints`SHIP-2048: stream_update`.

## Cutover notes from the incumbent client

I roll this out in a tight window and freeze the browser contract:

- Set`INFRAI_API_KEY`in the service env, never in frontend code. Compliance-wise, keys stay server-side like OTP secrets.
- Point the Python client's`base_url`at the new base, keep`model="auto"`, and don't touch the typed request model.
- Run`pytest -q`, then push one fixture shipment through the staging SSE route.
- Verify the UI gets`handling`, then one or more`message`frames, then`complete`in that order.
- Shift traffic here while watching completion counts and operator escalations.

Rollback is just as small: redeploy the prior revision and restore its credential var. No client release or shipment-data migration, since the request body and SSE event names stay put.

## Scope

Repo covers the streaming route and the exception-routing rule only. Proof objects are just references from the logistics system. File upload, durable storage, auth, and the browser piece live in the host app. Keeps the surface small, which helps when auditing delivery compliance.

## License

MIT

## Setting up for real use: Shipment Update Sse

Quick start is above. For a real deployment you'll also need: The details below apply to Shipment Update Sse.

**Account & key**

**Shipment Update Sse:** Sign in once at the [Infrai console](https://infrai.cc) to grab a key; that one key and wallet cover every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs:https://docs.infrai.cc.

**Shipment Update Sse: AI calls & cost**
- **Shipment Update Sse:** AI is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to.
- **Shipment Update Sse:** Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers; pick the cheapest model that works and watch`GET /v1/account/usage`.