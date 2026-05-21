# KoboSats — Backend

An offline-first financial tool for Nigeria's informal earners.

This repository contains the backend API for KoboSats. Built for the EVENTO Hack4Freedom 2026, it powers all USSD session handling, Bitcoin Lightning payments, debt tracking, Nostr record publishing, and SMS notifications. It serves both the USSD interface (via Africa's Talking) and the React web app through a single unified REST API.

## Tech Stack

- **Framework:** Python & FastAPI
- **Database:** SQLite (via SQLAlchemy)
- **Payments:** Bitnob Lightning API
- **USSD & SMS:** Africa's Talking API
- **Exchange Rate:** CoinGecko API
- **Decentralised Records:** Nostr Protocol
- **Deployment:** Render
