import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("🚀 KoboSats starting up...")
    
    from db.database import init_db
    init_db()
    print("✅ Database ready")

    from services.breez import breez_service
    await breez_service.connect()

    yield

    # Shutdown
    print("🛑 KoboSats shutting down...")
    from services.breez import breez_service
    await breez_service.disconnect()


app = FastAPI(
    title="KoboSats API",
    description="Bitcoin Lightning payments for Nigerian market traders",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://kobosat.netlify.app/", 
        "https://kobosat-backend.onrender.com",
        settings.FRONTEND_URL,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from routes.health import router as health_router
app.include_router(health_router, prefix="/api", tags=["Health"])

from routes.traders import router as traders_router
app.include_router(traders_router, prefix="/api/v1", tags=["Traders"])

from routes.lightning import router as lightning_router
app.include_router(lightning_router, prefix="/api/v1", tags=["Lightning"])

from routes.debts import router as debts_router
app.include_router(debts_router, prefix="/api/v1", tags=["Debts"])

from routes.ussd import router as ussd_router
app.include_router(ussd_router, prefix="/api/v1", tags=["USSD"])