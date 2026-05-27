from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Float
from db.database import Base

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    trader_phone = Column(String, index=True, nullable=False)
    amount_sats = Column(Float, nullable=False)
    amount_ngn = Column(Float, nullable=False)
    btc_ngn_rate = Column(Float, nullable=False)
    breez_invoice_hash = Column(String, unique=True, nullable=True)
    lightning_invoice   = Column(String, nullable=True)
    status = Column(String, default="pending")
    nostr_event_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    paid_at = Column(DateTime, nullable=True)