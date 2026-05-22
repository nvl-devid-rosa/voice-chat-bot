import os

from config import DEFAULT_MODEL_ID, DEFAULT_TEMPERATURE, INITIAL_MESSAGE, SYSTEM_PROMPT
from loguru import logger
from tools import salva_candidato

from line.llm_agent import LlmAgent, LlmConfig, end_call
from line.voice_agent_app import VoiceAgentApp


async def get_agent(env, call_request):
    """Crea l'agent HR per ogni nuova chiamata."""
    logger.info(
        f"Nuova chiamata HR: {call_request.call_id}. "
        f"Modello: {DEFAULT_MODEL_ID}"
    )

    return LlmAgent(
        model=f"anthropic/{DEFAULT_MODEL_ID}",
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        tools=[salva_candidato, end_call],
        config=LlmConfig.from_call_request(
            call_request,
            fallback_system_prompt=SYSTEM_PROMPT,
            fallback_introduction=INITIAL_MESSAGE,
        ),
        temperature=DEFAULT_TEMPERATURE,
    )


app = VoiceAgentApp(get_agent=get_agent)

if __name__ == "__main__":
    app.run()
