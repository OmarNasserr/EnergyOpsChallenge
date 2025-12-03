import uuid
from datetime import datetime, date

from sqlalchemy import DateTime, String, Date
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.contract import Base, utc_now


class Event(Base):
    __tablename__ = "event"

    id: Mapped[uuid.UUID] = mapped_column(
        default=uuid.uuid4, primary_key=True, index=True
    )
    contract_number: Mapped[str] = mapped_column(String, nullable=False, index=True)
    component_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
