# HR Voice Agent

Voice agent per raccolta profili candidati via Cartesia Line.

## Setup

```bash
uv sync
cartesia auth login
cp .env.example .env  # compila le variabili
PORT=8000 uv run python main.py
```
