# WhatsApp Bridge

Autonomous WhatsApp AI Bridge with multi-service architecture.

## Architecture

- **Bot Service** (Node.js, Baileys) — WhatsApp connection on port 5057
- **JARVIS AGI** (Python/Flask) — AI orchestration on port 5052
- **Flask Handler** (Python/Flask) — WhatsApp message handling on port 5056

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your API keys
3. Run `npm install`
4. Run `npm start`

## Commands

- `/start` — Initialize the bot
- `/help` — Show available commands
- `/status` — Check bot status
- `/jobs` — List available jobs
- `/leads` — View leads
- `/notes` — Manage notes
- `/remind` — Set reminders
- `/search` — Search knowledge base
- `/summarize` — Summarize content
- `/translate` — Translate text
- `/name` — Set your name
- `/clear` — Clear conversation

## Autonomy

This project uses autonomous management. See `MANAGEMENT.md` for details.

Run `npm run agent` to interact with the management system.

## Security

**Never commit `.env` or database files.** All sensitive data is in `.env` (gitignored).

## License

MIT
