"""
Test del HR voice agent con Claude.

Esegui con:
    uv sync --extra dev
    uv run pytest test_hr_agent.py -v

Con parallelismo:
    uv run pytest test_hr_agent.py --count 4 -n auto
"""

import os

import pytest
from config import DEFAULT_MODEL_ID, DEFAULT_TEMPERATURE, SYSTEM_PROMPT
from tools import salva_candidato

from line.evals.conversation_runner import ConversationRunner
from line.evals.turn import AgentTurn, UserTurn
from line.events import EndCall
from line.llm_agent import LlmAgent, LlmConfig, end_call


@pytest.fixture
def hr_agent():
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY non configurata")

    return LlmAgent(
        model=f"anthropic/{DEFAULT_MODEL_ID}",
        api_key=api_key,
        tools=[salva_candidato, end_call],
        config=LlmConfig(
            system_prompt=SYSTEM_PROMPT,
            introduction="Ciao! Sono l'assistente HR.",
        ),
        temperature=DEFAULT_TEMPERATURE,
    )


@pytest.mark.asyncio
async def test_saluto_iniziale(hr_agent):
    """L'agent risponde al saluto e inizia a raccogliere info."""
    conv = [
        UserTurn(text="Ciao"),
        AgentTurn(text=["<chiede del candidato>", "<chiede nome>"]),
    ]
    await ConversationRunner(hr_agent, conv).run()


@pytest.mark.asyncio
async def test_raccolta_dati_base(hr_agent):
    """L'agent raccoglie nome, cognome e ruolo in modo conversazionale."""
    conv = [
        UserTurn(text="Ho conosciuto un candidato interessante al convegno DevOps"),
        AgentTurn(text=["<chiede nome>", "<chiede cognome>", "<chiede candidato>"]),
        UserTurn(text="Si chiama Mario Rossi"),
        AgentTurn(text=["<chiede ruolo>", "<chiede posizione>", "<chiede skills>"]),
        UserTurn(text="È un DevOps engineer con 5 anni di esperienza in Kubernetes"),
        AgentTurn(text=["<conferma>", "<chiede conferma>", "<vuole salvare>"]),
    ]
    await ConversationRunner(hr_agent, conv).run()


@pytest.mark.asyncio
async def test_salvataggio_con_conferma(hr_agent):
    """L'agent salva il candidato e termina la chiamata dopo conferma."""
    conv = [
        UserTurn(text="Ho conosciuto Mario Rossi, DevOps engineer, skills: Kubernetes e Terraform"),
        AgentTurn(text=["<chiede conferma>", "<vuole salvare>"]),
        UserTurn(text="Sì, salva pure"),
        AgentTurn(
            text=["<conferma salvataggio>", "<saluta>", "<arrivederci>"],
            telephony_events=[EndCall()],
        ),
    ]
    await ConversationRunner(hr_agent, conv).run()


@pytest.mark.asyncio
async def test_fine_chiamata_esplicita(hr_agent):
    """L'agent termina la chiamata se l'utente saluta."""
    conv = [
        UserTurn(text="No grazie, per ora è tutto. Arrivederci"),
        AgentTurn(
            text="*",
            telephony_events=[EndCall()],
        ),
    ]
    await ConversationRunner(hr_agent, conv).run()


@pytest.mark.asyncio
async def test_dati_opzionali(hr_agent):
    """L'agent raccoglie email e telefono se forniti."""
    conv = [
        UserTurn(
            text="Mario Rossi, DevOps, Kubernetes. La sua email è mario@rossi.it "
                 "e il telefono è 333 1234567"
        ),
        AgentTurn(text=["<conferma dati>", "<chiede conferma salvataggio>"]),
    ]
    await ConversationRunner(hr_agent, conv).run()

