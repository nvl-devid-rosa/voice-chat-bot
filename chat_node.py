"""
HrChatNode - Voice agent node per raccolta dati candidati HR.
Adattato per usare Anthropic Claude al posto di Google Gemini.
"""

import asyncio
import random
from typing import AsyncGenerator, Optional, Union

import aiohttp
import anthropic
from config import DEFAULT_MODEL_ID, DEFAULT_TEMPERATURE, N8N_API_KEY, N8N_WEBHOOK_URL
from loguru import logger

from line.events import AgentResponse, EndCall
from line.nodes.conversation_context import ConversationContext
from line.nodes.reasoning import ReasoningNode
from line.tools.system_tools import EndCallArgs, EndCallTool, end_call
from line.utils.gemini_utils import convert_messages_to_gemini


# ── Tool definition ────────────────────────────────────────────────────────────

SALVA_CANDIDATO_TOOL = {
    "name": "salva_candidato",
    "description": (
        "Salva il profilo del candidato nel sistema HR e termina la chiamata. "
        "Chiamare SOLO dopo conferma esplicita del manager."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "nome":              {"type": "string", "description": "Nome del candidato"},
            "cognome":           {"type": "string", "description": "Cognome del candidato"},
            "ruolo":             {"type": "string", "description": "Ruolo o posizione professionale"},
            "skills":            {"type": "string", "description": "Skills o competenze, separate da virgola"},
            "note":              {"type": "string", "description": "Note aggiuntive"},
            "email":             {"type": "string", "description": "Email del candidato (opzionale)"},
            "telefono":          {"type": "string", "description": "Telefono del candidato (opzionale)"},
            "messaggio_congedo": {"type": "string", "description": "Messaggio di saluto finale"},
        },
        "required": ["nome", "cognome", "ruolo", "skills", "messaggio_congedo"],
    },
}

END_CALL_TOOL = {
    "name": "end_call",
    "description": "Termina la chiamata con un messaggio di saluto.",
    "input_schema": {
        "type": "object",
        "properties": {
            "goodbye_message": {"type": "string", "description": "Messaggio di arrivederci"},
        },
        "required": ["goodbye_message"],
    },
}


async def _invia_a_n8n(payload: dict) -> bool:
    """Invia il payload al webhook n8n. Ritorna True se successo."""
    if not N8N_WEBHOOK_URL:
        logger.warning("N8N_WEBHOOK_URL non configurato — salvataggio simulato")
        logger.info(f"Payload simulato: {payload}")
        return True

    headers = {"Content-Type": "application/json"}
    if N8N_API_KEY:
        headers["X-API-Key"] = N8N_API_KEY

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                N8N_WEBHOOK_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status == 200:
                    logger.info(f"Candidato salvato su n8n: {payload['nome']} {payload['cognome']}")
                    return True
                else:
                    logger.error(f"n8n ha risposto con status {resp.status}")
                    return False
    except Exception as e:
        logger.error(f"Errore invio a n8n: {e}")
        return False


# ── Node principale ────────────────────────────────────────────────────────────

class HrChatNode(ReasoningNode):
    """
    Voice agent node per raccolta dati candidati HR.
    Usa Anthropic Claude con streaming e tool use.
    """

    def __init__(
        self,
        system_prompt: str,
        anthropic_client: Optional[anthropic.AsyncAnthropic] = None,
        model_id: str = DEFAULT_MODEL_ID,
        temperature: float = DEFAULT_TEMPERATURE,
        max_context_length: int = 100,
        max_output_tokens: int = 500,
    ):
        super().__init__(system_prompt=system_prompt, max_context_length=max_context_length)

        self.client = anthropic_client
        self.model_id = model_id
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.tools = [SALVA_CANDIDATO_TOOL, END_CALL_TOOL]

        logger.info(f"HrChatNode inizializzato con modello: {model_id}")

    async def process_context(
        self, context: ConversationContext
    ) -> AsyncGenerator[Union[AgentResponse, EndCall], None]:
        if not context.events:
            return

        messages = convert_messages_to_gemini(context.get_committed_events())
        user_message = context.get_latest_user_transcript_message()
        if user_message:
            logger.info(f'🧠 Manager: "{user_message}"')

        if not self.client:
            yield AgentResponse(content="Nessun client Anthropic configurato. Aggiungi ANTHROPIC_API_KEY alle variabili d'ambiente.")
            return

        full_response = ""

        async with self.client.messages.stream(
            model=self.model_id,
            max_tokens=self.max_output_tokens,
            system=self.system_prompt,
            messages=messages,
            tools=self.tools,
            temperature=self.temperature,
        ) as stream:
            async for event in stream:

                # Testo in streaming
                if event.type == "content_block_delta" and event.delta.type == "text_delta":
                    chunk = event.delta.text
                    full_response += chunk
                    yield AgentResponse(content=chunk)

                # Tool use completato
                elif event.type == "content_block_stop":
                    final_msg = await stream.get_final_message()

                    for block in final_msg.content:
                        if block.type != "tool_use":
                            continue

                        # ── salva_candidato ──────────────────────────────────
                        if block.name == "salva_candidato":
                            args = block.input
                            logger.info(f"💾 Salvataggio candidato: {args.get('nome')} {args.get('cognome')}")

                            payload = {
                                "canale": "voce",
                                "nome": args.get("nome", ""),
                                "cognome": args.get("cognome", ""),
                                "note": (
                                    f"Ruolo: {args.get('ruolo', '')}\n"
                                    f"Skills: {args.get('skills', '')}\n"
                                    f"Note: {args.get('note', '')}"
                                ),
                                "email": args.get("email", ""),
                                "telefono": args.get("telefono", ""),
                            }

                            successo = await _invia_a_n8n(payload)
                            congedo = (
                                args.get("messaggio_congedo", "Perfetto, ho salvato il profilo. Grazie e buona giornata!")
                                if successo
                                else "Mi dispiace, c'è stato un problema tecnico nel salvataggio. Riprovi più tardi."
                            )

                            yield AgentResponse(content=congedo)
                            async for item in end_call(EndCallArgs(goodbye_message="")):
                                yield item

                        # ── end_call esplicito ───────────────────────────────
                        elif block.name == "end_call":
                            goodbye = block.input.get("goodbye_message", "Arrivederci!")
                            logger.info(f"📞 Fine chiamata: {goodbye}")
                            async for item in end_call(EndCallArgs(goodbye_message=goodbye)):
                                yield item

                    break  # stop dopo il primo content_block_stop con tool

        if full_response:
            logger.info(f'🤖 Agent: "{full_response}"')
