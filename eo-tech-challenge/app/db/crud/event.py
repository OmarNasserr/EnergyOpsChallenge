from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.event import Event
from app.dto.event import EventPayload


async def create_event(db: AsyncSession, payload: EventPayload, component_name: str) -> Event:
    """Create a new event in the database."""
    event = Event(
        contract_number=payload.contract_number,
        component_name=component_name,
        type=payload.type,
        date=payload.date,
        created_at=payload.created_at,
    )
    db.add(event)

    try:
        await db.commit()
        await db.refresh(event)
    except SQLAlchemyError:
        await db.rollback()
        raise

    return event


async def get_events_for_contract(
    db: AsyncSession, contract_number: str
) -> list[Event]:
    """
    Get all events for a specific contract, ordered by created_at.
    Events are processed in the order they were created.
    """
    result = await db.scalars(
        select(Event)
        .where(Event.contract_number == contract_number)
        .order_by(Event.created_at)
    )
    return list(result.all())
