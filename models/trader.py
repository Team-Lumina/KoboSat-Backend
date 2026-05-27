from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Float
from db.database import Base

class Trader(Base):
    __tablename__ = "traders"

    id = Column(Integer, primary_key=True, index=True)
    phone_number = Column(String, unique=True, index=True, nullable=False)
    language = Column(String, default="en")
    nostr_pubkey = Column(String, nullable=True)
    nostr_privkey = Column(String, nullable=True)
    balance_sats = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)