import asyncio
from types import SimpleNamespace

from logistics_policy import HandlingDecision, ShipmentBrief, decide_handling
from shipment_stream import stream_shipment_update


def test_damage_exception_escalates_even_with_signed_proof() -> None:
    shipment = ShipmentBrief.model_validate(
        {
            "shipment_id": "SHIP-91",
            "events": [
                {"kind": "delivered", "occurred_at": "2026-09-28T09:40:00Z"}
            ],
            "proof_of_delivery": [
                {
                    "name": "doorstep.jpg",
                    "media_type": "image/jpeg",
                    "download_url": "https://example.test/proofs/doorstep.jpg",
                }
            ],
            "exception": {
                "category": "damaged_parcel",
                "detail": "Carton arrived crushed",
            },
        }
    )

    assert decide_handling(shipment) is HandlingDecision.ESCALATE_TO_OPERATOR


def test_completed_delivery_with_proof_can_stream_normally() -> None:
    shipment = ShipmentBrief.model_validate(
        {
            "shipment_id": "SHIP-92",
            "events": [
                {"kind": "delivered", "occurred_at": "2026-09-28T10:15:00Z"}
            ],
            "proof_of_delivery": [
                {
                    "name": "signature.pdf",
                    "media_type": "application/pdf",
                    "download_url": "https://example.test/proofs/signature.pdf",
                }
            ],
        }
    )

    assert decide_handling(shipment) is HandlingDecision.STREAM_UPDATE


def test_stream_ignores_metadata_chunks_without_choices() -> None:
    shipment = ShipmentBrief.model_validate(
        {
            "shipment_id": "SHIP-93",
            "events": [{"kind": "delivered", "occurred_at": "2026-09-28T10:15:00Z"}],
            "proof_of_delivery": [
                {
                    "name": "signature.pdf",
                    "media_type": "application/pdf",
                    "download_url": "https://example.test/proofs/signature.pdf",
                }
            ],
        }
    )

    async def chunks():
        yield SimpleNamespace(choices=[])
        yield SimpleNamespace(
            choices=[SimpleNamespace(delta=SimpleNamespace(content="Delivered."))]
        )

    async def create(**_):
        return chunks()

    ai = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )

    async def collect_frames() -> list[str]:
        return [frame async for frame in stream_shipment_update(shipment, ai)]

    frames = asyncio.run(collect_frames())

    assert frames == [
        'event: handling\ndata: {"decision":"stream_update"}\n\n',
        'event: message\ndata: {"text":"Delivered."}\n\n',
        'event: complete\ndata: {"shipment_id":"SHIP-93"}\n\n',
    ]
