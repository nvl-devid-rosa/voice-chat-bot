import os

from dotenv import load_dotenv

# Carica le variabili d'ambiente dal file .env PRIMA di tutti gli altri import
load_dotenv()

from config import (
    DEFAULT_MODEL_ID,
    INITIAL_MESSAGE,
    LITELLM_MODEL,
    SYSTEM_PROMPT,
)
from loguru import logger
from tools import salva_candidato

from line.llm_agent import LlmAgent, LlmConfig, end_call
from line.voice_agent_app import VoiceAgentApp


# ── Check variabili d'ambiente critiche ───────────────────────────────────────

if not os.getenv("ANTHROPIC_API_KEY"):
    raise RuntimeError(
        "ANTHROPIC_API_KEY non trovata. Configurala nel file .env "
        "(vedi README per le istruzioni)."
    )

if not os.getenv("N8N_WEBHOOK_URL"):
    logger.warning(
        "N8N_WEBHOOK_URL non configurato — i candidati verranno solo loggati, "
        "non inviati a n8n."
    )


# ── Agent factory ─────────────────────────────────────────────────────────────

async def get_agent(env, call_request):
    """Crea l'agent HR per ogni nuova chiamata."""
    logger.info(
        f"Nuova chiamata HR: {call_request.call_id}. Modello: {DEFAULT_MODEL_ID}"
    )

    return LlmAgent(
        model=LITELLM_MODEL,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        tools=[salva_candidato, end_call],
        config=LlmConfig.from_call_request(
            call_request,
            fallback_system_prompt=SYSTEM_PROMPT,
            fallback_introduction=INITIAL_MESSAGE,
        ),
    )


app = VoiceAgentApp(get_agent=get_agent)


if __name__ == "__main__":
    app.run()
