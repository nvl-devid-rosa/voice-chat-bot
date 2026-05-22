"""
Tool salva_candidato: invia i dati raccolti durante la conversazione
al webhook n8n per l'elaborazione HR.
"""

from typing import Annotated

import aiohttp
from config import N8N_API_KEY, N8N_WEBHOOK_URL
from loguru import logger

from line.llm_agent import loopback_tool


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

    logger.info(f"📋 Payload pronto per n8n: {payload}")

    # Modalità simulazione (utile per testing senza n8n configurato)
    if not N8N_WEBHOOK_URL:
        logger.warning("N8N_WEBHOOK_URL non configurato — salvataggio simulato")
        return (
            f"Candidato {nome} {cognome} registrato in modalità simulazione. "
            "Ringrazia il manager e termina la chiamata con end_call."
        )

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
                body = await resp.text()

                if resp.status == 200:
                    logger.info(
                        f"💾 Candidato salvato su n8n: {nome} {cognome} "
                        f"(status: {resp.status})"
                    )
                    return (
                        f"Candidato {nome} {cognome} salvato correttamente nel sistema HR. "
                        "Ringrazia il manager e termina la chiamata con end_call."
                    )
                else:
                    logger.error(
                        f"n8n ha risposto con status {resp.status}: {body[:200]}"
                    )
                    return (
                        "Si è verificato un problema tecnico nel salvataggio. "
                        "Comunica al manager che riproveremo più tardi e termina la chiamata."
                    )
    except aiohttp.ClientError as e:
        logger.error(f"Errore di connessione a n8n: {e}")
        return (
            "Errore di connessione al sistema HR. "
            "Comunica al manager che riproveremo più tardi e termina la chiamata."
        )
    except Exception as e:
        logger.error(f"Errore inatteso durante invio a n8n: {e}")
        return (
            "Errore inatteso nel salvataggio. "
            "Comunica al manager che riproveremo più tardi e termina la chiamata."
        )
