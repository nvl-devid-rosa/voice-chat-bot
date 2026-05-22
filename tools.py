"""
HR Voice Agent — usa l'LlmAgent ufficiale di Cartesia Line con Claude.

A differenza del template Gemini (che implementava un ReasoningNode custom),
qui sfruttiamo LlmAgent + LiteLLM che supporta nativamente Claude.
Più semplice, meno codice, stessa funzionalità.
"""

from typing import Annotated

import aiohttp
from config import DEFAULT_MODEL_ID, DEFAULT_TEMPERATURE, N8N_API_KEY, N8N_WEBHOOK_URL
from loguru import logger

from line.llm_agent import LlmAgent, LlmConfig, end_call, loopback_tool


# ── Tool: salva candidato su n8n ──────────────────────────────────────────────

@loopback_tool
async def salva_candidato(
    ctx,
    nome: Annotated[str, "Nome del candidato"],
    cognome: Annotated[str, "Cognome del candidato"],
    ruolo: Annotated[str, "Ruolo o posizione professionale"],
    skills: Annotated[str, "Skills o competenze, separate da virgola"],
    note: Annotated[str, "Note aggiuntive: contesto incontro, anni esperienza, azienda"] = "",
    email: Annotated[str, "Email del candidato"] = "",
    telefono: Annotated[str, "Telefono del candidato"] = "",
) -> str:
    """
    Salva il profilo del candidato nel sistema HR.
    Chiamare SOLO dopo conferma esplicita del manager.
    """
    payload = {
        "canale": "voce",
        "nome": nome,
        "cognome": cognome,
        "note": (
            f"Ruolo: {ruolo}\n"
            f"Skills: {skills}\n"
            f"Note: {note}"
        ),
        "email": email,
        "telefono": telefono,
    }

    if not N8N_WEBHOOK_URL:
        logger.warning("N8N_WEBHOOK_URL non configurato — salvataggio simulato")
        logger.info(f"Payload simulato: {payload}")
        return f"Candidato {nome} {cognome} salvato (simulazione). Puoi terminare la chiamata."

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
                    logger.info(f"💾 Candidato salvato: {nome} {cognome}")
                    return (
                        f"Candidato {nome} {cognome} salvato correttamente nel sistema HR. "
                        "Ringrazia il manager e termina la chiamata con end_call."
                    )
                else:
                    logger.error(f"n8n status {resp.status}")
                    return (
                        "Errore tecnico nel salvataggio. "
                        "Comunica al manager di riprovare più tardi."
                    )
    except Exception as e:
        logger.error(f"Errore invio a n8n: {e}")
        return (
            "Errore di connessione nel salvataggio. "
            "Comunica al manager di riprovare più tardi."
        )
