from sqlalchemy import Column, String, Integer, DateTime, Float
from sqlalchemy.sql import func
from db.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    trader_phone = Column(String, index=True, nullable=False)
    amount_sats = Column(Float, nullable=False)
    amount_ngn = Column(Float, nullable=False)
    btc_ngn_rate = Column(Float, nullable=False)
    bitnob_invoice_id = Column(String, nullable=True)
    status = Column(String, default="pending")
    nostr_event_id = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())