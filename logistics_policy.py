"""Deterministic shipment decisions kept outside the model call."""

from enum import StrEnum

from pydantic import BaseModel, Field


class ShipmentEvent(BaseModel):
    kind: str = Field(min_length=1)
    occurred_at: str = Field(min_length=1)
    note: str | None = None


class ProofOfDelivery(BaseModel):
    name: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    download_url: str = Field(min_length=1)


class ShipmentException(BaseModel):
    category: str = Field(min_length=1)
    detail: str = Field(min_length=1)


class HandlingDecision(StrEnum):
    STREAM_UPDATE = "stream_update"
    ESCALATE_TO_OPERATOR = "escalate_to_operator"


class ShipmentBrief(BaseModel):
    shipment_id: str = Field(min_length=1)
    events: list[ShipmentEvent] = Field(min_length=1)
    proof_of_delivery: list[ProofOfDelivery] = Field(default_factory=list)
    exception: ShipmentException | None = None


def decide_handling(shipment: ShipmentBrief) -> HandlingDecision:
    """Keep operational routing predictable while AI writes the timeline."""
    if shipment.exception is not None or not shipment.proof_of_delivery:
        return HandlingDecision.ESCALATE_TO_OPERATOR
    return HandlingDecision.STREAM_UPDATE


def build_dispatch_prompt(shipment: ShipmentBrief, decision: HandlingDecision) -> str:
    event_lines = "\n".join(
        f"- {event.occurred_at}: {event.kind}"
        + (f" ({event.note})" if event.note else "")
        for event in shipment.events
    )
    proof_names = ", ".join(proof.name for proof in shipment.proof_of_delivery) or "none"
    exception = (
        f"{shipment.exception.category}: {shipment.exception.detail}"
        if shipment.exception
        else "none"
    )
    return (
        f"Write a concise customer-facing logistics update for shipment {shipment.shipment_id}.\n"
        f"Events:\n{event_lines}\n"
        f"Proof-of-delivery files: {proof_names}\n"
        f"Exception: {exception}\n"
        f"Handling decision: {decision.value}. "
        "State confirmed facts only and do not invent dates or delivery details."
    )

