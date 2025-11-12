# Security Policy

- Secrets are sourced exclusively from environment variables (`BINANCE_API_KEY`, `BINANCE_API_SECRET`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`).
- Do not commit `.env` files; use `.env.sample` as reference.
- Rotate API keys before promoting to live mode.
- Report vulnerabilities by opening a private security advisory via GitHub Security.
