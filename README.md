# HR Voice Agent

Voice agent per raccolta profili candidati via Cartesia Line + Claude.
Il manager chiama, descrive il candidato incontrato, i dati vengono
inviati automaticamente al workflow n8n per l'elaborazione HR.

## Struttura

```
├── main.py          # Entry point — definisce l'LlmAgent
├── tools.py         # Tool salva_candidato che invia a n8n
├── config.py        # System prompt, variabili d'ambiente
├── test_hr_agent.py # Test conversazionali
├── pyproject.toml   # Dipendenze Python
└── .env             # Variabili locali (non committare)
```

## Prerequisiti

- [Account Cartesia](https://play.cartesia.ai) + CLI installata
- [Anthropic API key](https://console.anthropic.com)
- Workflow n8n attivo con webhook configurato

## Variabili d'ambiente

| Variabile | Descrizione | Obbligatoria |
|-----------|-------------|--------------|
| `ANTHROPIC_API_KEY` | Anthropic API key | Sì |
| `N8N_WEBHOOK_URL` | URL webhook n8n candidato-voce | Sì |
| `N8N_API_KEY` | Header auth del webhook n8n | Consigliata |
| `MODEL_ID` | Modello Claude (default: claude-sonnet-4-5) | No |

Crea un file `.env` nella root del progetto:
```
ANTHROPIC_API_KEY=sk-ant-...
N8N_WEBHOOK_URL=https://tuon8n.app.n8n.cloud/webhook/candidato-voce
N8N_API_KEY=your_api_key_here
```

## Setup locale

### 1. Installa la CLI Cartesia
```zsh
curl -fsSL https://cartesia.sh | sh
cartesia auth login
```

### 2. Installa dipendenze e avvia
```zsh
# Con uv (consigliato)
PORT=8000 uv run python main.py

# Con pip
python -m venv .venv
source .venv/bin/activate
pip install -e .
PORT=8000 python main.py
```

### 3. Testa localmente (in un altro terminale)
```zsh
cartesia chat 8000
```

## Deploy su Cartesia Cloud
```zsh
cartesia deploy
```

## Configurazione n8n

Aggiungi nel workflow esistente:

1. **Webhook** — path: `candidato-voce`, method: POST, auth: Header Auth
2. **Edit Fields** — aggiungi `canale: voce`
3. Collega al nodo `Code in JavaScript1` già esistente

Il payload inviato dal voice agent è:
```json
{
  "canale": "voce",
  "nome": "Mario",
  "cognome": "Rossi",
  "note": "Ruolo: DevOps\nSkills: Kubernetes, Terraform\nNote: conosciuto al convegno",
  "email": "",
  "telefono": ""
}
```

## Test
```zsh
uv sync --extra dev
uv run pytest test_hr_agent.py -v
```

## Note sull'architettura

A differenza del template base `basic_chat` (che implementa un `ReasoningNode` custom per Gemini), 
questo progetto usa direttamente l'**LlmAgent** ufficiale di Cartesia Line, che supporta Claude 
nativamente via LiteLLM. 

Vantaggi:
- Meno codice da mantenere (no `chat_node.py` custom)
- Tool calling gestito automaticamente dal framework
- Possibilità di switchare modello (Claude/GPT/Gemini) cambiando solo la stringa `model`

