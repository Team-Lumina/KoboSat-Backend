from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from config import settings

if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
else:
    db_url = settings.DATABASE_URL.replace(
        "postgres://", "postgresql://", 1
    )
    engine = create_engine(db_url)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    from models import trader, transaction, debt  # noqa: F401

    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")