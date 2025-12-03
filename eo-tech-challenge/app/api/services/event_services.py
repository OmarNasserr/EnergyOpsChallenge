from datetime import date

from fastapi import HTTPException
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.crud.contract import get_contract
from app.db.crud.event import create_event, get_events_for_contract
from app.db.models.event import Event
from app.dto.event import (
    ComponentTimeline,
    ContractTimelineResponse,
    EventPayload,
    EventResponse,
)

# Allowed components
ALLOWED_COMPONENTS = [
    "energy_supply",
    "battery_optimization",
    "heatpump_optimization",
]

# Supported event types
VALID_EVENT_TYPES = [
    "supply_energy_start",
    "supply_energy_end",
    "battery_optimization_start",
    "battery_optimization_end",
    "heatpump_optimization_start",
    "heatpump_optimization_end",
]

# Mapping from event type prefix to component name
EVENT_TYPE_TO_COMPONENT = {
    "supply_energy": "energy_supply",
    "battery_optimization": "battery_optimization",
    "heatpump_optimization": "heatpump_optimization",
}


def get_component_name(event_type: str) -> str | None:
    """
    Extract component name from event type.

    Examples:
        supply_energy_start -> energy_supply
        battery_optimization_end -> battery_optimization
        heatpump_optimization_start -> heatpump_optimization

    Returns:
        Component name if valid, None otherwise
    """
    for prefix, component in EVENT_TYPE_TO_COMPONENT.items():
        if event_type.startswith(prefix):
            # Validate component is in allowed list
            if component in ALLOWED_COMPONENTS:
                return component
            return None
    return None


def build_timeline(events: list[Event]) -> dict[str, dict[str, date | None]]:
    """
    Build component timeline from events.
    Events must be sorted by created_at (ascending order).

    Rules:
    - Later start events overwrite earlier start events
    - Later end events overwrite earlier end events
    - Each component has start and end fields (can be None)

    Returns:
        Dictionary mapping component names to their timeline state.
        Example: {"energy_supply": {"start": date(2024, 12, 1), "end": date(2024, 12, 31)}}
    """
    timeline: dict[str, dict[str, date | None]] = {}

    for event in events:
        component = get_component_name(event.type)

        # Skip events with invalid component names (shouldn't happen with validation)
        if component is None:
            continue

        if component not in timeline:
            timeline[component] = {"start": None, "end": None}

        if event.type.endswith("_start"):
            timeline[component]["start"] = event.date
        elif event.type.endswith("_end"):
            timeline[component]["end"] = event.date

    return timeline


async def handle_event_creation(
    db: AsyncSession, payload: EventPayload
) -> EventResponse:
    """
    Process a single event with validation.

    Business Rules:
    1. Contract must exist
    2. Event type must be valid
    3. End event cannot come before start event
    4. Start event cannot come after end event
    5. End event requires a start event first
    """
    logger.info(
        f"Processing event: {payload.type} for contract {payload.contract_number}"
    )

    # 1. Validate event type
    if payload.type not in VALID_EVENT_TYPES:
        logger.warning(f"Invalid event type: {payload.type}")
        return EventResponse(
            status="rejected", message=f"Invalid event type: {payload.type}"
        )

    # 2. Validate component (extract and check if allowed)
    component_name = get_component_name(payload.type)
    if component_name is None:
        logger.warning(f"Unsupported component for event type: {payload.type}")
        return EventResponse(
            status="rejected",
            message=f"Unsupported component for event type: {payload.type}",
        )

    # 3. Check if contract exists
    contract = await get_contract(db, payload.contract_number)
    if not contract:
        logger.warning(f"Contract {payload.contract_number} not found")
        return EventResponse(
            status="rejected",
            message=f"Contract {payload.contract_number} not found.",
        )

    # 4. Validate component is in the contract
    if component_name not in contract.components:
        logger.warning(
            f"Component {component_name} not available in contract {payload.contract_number}"
        )
        return EventResponse(
            status="rejected",
            message=f"Component '{component_name}' is not available in contract {payload.contract_number}.",
        )

    # 5. Get all existing events for this contract (sorted by created_at)
    events = await get_events_for_contract(db, payload.contract_number)

    # 6. Build current timeline state from existing events
    timeline = build_timeline(events)

    # 7. Determine if this is a start or end event
    is_start_event = payload.type.endswith("_start")

    # 8. Get current state for this component
    component_state = timeline.get(component_name, {"start": None, "end": None})
    current_start = component_state["start"]
    current_end = component_state["end"]

    # 9. Validate the new event against current timeline state
    if is_start_event:
        # Start event validation

        # Rule: Component cannot be restarted once terminated
        # A component is terminated if it has both start and end dates
        if current_start and current_end:
            logger.warning(
                f"Cannot restart component {component_name} - already terminated"
            )
            return EventResponse(
                status="rejected",
                message="Component cannot be restarted after termination.",
            )

        # Rule: Start event cannot come after end event
        if current_end and payload.date > current_end:
            logger.warning(
                f"Start event date {payload.date} is after end event date {current_end}"
            )
            return EventResponse(
                status="rejected",
                message="Start event cannot occur after end event.",
            )
    else:
        # End event validation

        # Rule: End event requires a start event first
        if not current_start:
            logger.warning(f"End event without start event for {component_name}")
            return EventResponse(
                status="rejected", message="End event requires a start event first."
            )

        # Rule: End event cannot come before start event
        if payload.date < current_start:
            logger.warning(
                f"End event date {payload.date} is before start event date {current_start}"
            )
            return EventResponse(
                status="rejected",
                message="End event cannot occur before start event.",
            )

    # 10. All validations passed - save the event with component_name
    await create_event(db, payload, component_name)

    logger.info(
        f"Event accepted: {payload.type} for contract {payload.contract_number}"
    )
    return EventResponse(status="accepted", message="Event processed successfully.")


async def handle_timeline_retrieval(
    db: AsyncSession, contract_number: str
) -> ContractTimelineResponse:
    """
    Get timeline for all components of a contract.

    Returns the start and end dates for each component defined in the contract.
    Components without events will have null start and end dates.
    """
    logger.info(f"Retrieving timeline for contract {contract_number}")

    # 1. Check if contract exists
    contract = await get_contract(db, contract_number)
    if not contract:
        logger.warning(f"Contract {contract_number} not found")
        raise HTTPException(
            status_code=404, detail=f"Contract {contract_number} not found."
        )

    # 2. Get all events for this contract
    events = await get_events_for_contract(db, contract_number)

    # 3. Build timeline from events
    timeline = build_timeline(events)

    # 4. Format response - include all components from contract
    components: dict[str, ComponentTimeline] = {}

    for component in contract.components:
        if component in timeline:
            components[component] = ComponentTimeline(
                start=timeline[component]["start"], end=timeline[component]["end"]
            )
        else:
            # Component has no events yet
            components[component] = ComponentTimeline(start=None, end=None)

    logger.info(f"Timeline retrieved for contract {contract_number}")
    return ContractTimelineResponse(
        contract_number=contract_number, components=components
    )
