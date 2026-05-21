from sqlalchemy import Column, String, Integer, DateTime, Float
from sqlalchemy.sql import func
from db.database import Base

class Debt(Base):
    __tablename__ = "debts"

    id = Column(Integer, primary_key=True, index=True)
    debt_id = Column(String, unique=True, index=True)
    creditor_phone = Column(String, index=True, nullable=False)
    debtor_phone = Column(String, nullable=False)
    amount_ngn = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(String, default="pending")
    nostr_event_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    settled_at = Column(DateTime(timezone=True), nullable=True)