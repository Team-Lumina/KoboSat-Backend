from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Breez SDK
    BREEZ_API_KEY: str = ""
    BREEZ_MNEMONIC: str = ""
    BREEZ_STORAGE_DIR: str = "./.breez_data"

    # Africa's Talking
    AT_API_KEY: str = ""
    AT_USERNAME: str = "sandbox"

    # CoinGecko
    COINGECKO_BASE_URL: str = "https://api.coingecko.com/api/v3"

    # Database
    DATABASE_URL: str = "sqlite:///./kobosats.db"

    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "change-this-in-production"
    FRONTEND_URL: str = "http://localhost:5173"

    # Nostr relays — comma separated
    NOSTR_RELAYS: str = "wss://relay.damus.io,wss://relay.nostr.band,wss://nos.lol"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()