"""Print the same deterministic decision the HTTP route streams first."""

from logistics_policy import ShipmentBrief, decide_handling


sample = ShipmentBrief.model_validate(
    {
        "shipment_id": "SHIP-2048",
        "events": [
            {
                "kind": "delivered",
                "occurred_at": "2026-09-28T09:40:00Z",
                "note": "Left with receiving desk",
            }
        ],
        "proof_of_delivery": [
            {
                "name": "signed-receipt.pdf",
                "media_type": "application/pdf",
                "download_url": "https://example.test/proofs/signed-receipt.pdf",
            }
        ],
    }
)

print(f"{sample.shipment_id}: {decide_handling(sample).value}")

