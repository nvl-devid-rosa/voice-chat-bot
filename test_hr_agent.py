import os
import pytest
from chat_node import HrChatNode
from config import SYSTEM_PROMPT
from google import genai

from line.evals.conversation_runner import ConversationRunner
from line.evals.turn import AgentTurn, UserTurn
from line.events import EndCall


@pytest.fixture
def gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        pytest.skip("GEMINI_API_KEY non configurata")
    return genai.Client(api_key=api_key)

@pytest.fixture
def hr_node(gemini_client):
    return HrChatNode(system_prompt=SYSTEM_PROMPT, gemini_client=gemini_client)

@pytest.mark.asyncio
async def test_saluto_iniziale(hr_node):
    conv = [
        UserTurn(text="Ciao"),
        AgentTurn(text=["<chiede del candidato>", "<chiede nome>"]),
    ]
    await ConversationRunner(hr_node, conv).run()

@pytest.mark.asyncio
async def test_raccolta_dati_base(hr_node):
    conv = [
        UserTurn(text="Ho conosciuto un candidato interessante al convegno DevOps"),
        AgentTurn(text=["<chiede nome>", "<chiede cognome>", "<chiede candidato>"]),
        UserTurn(text="Si chiama Mario Rossi"),
        AgentTurn(text=["<chiede ruolo>", "<chiede posizione>", "<chiede skills>"]),
        UserTurn(text="È un DevOps engineer con 5 anni di esperienza in Kubernetes"),
        AgentTurn(text=["<conferma>", "<chiede conferma>", "<vuole salvare>"]),
    ]
    await ConversationRunner(hr_node, conv).run()

@pytest.mark.asyncio
async def test_salvataggio_con_conferma(hr_node):
    conv = [
        UserTurn(text="Ho conosciuto Mario Rossi, DevOps engineer, skills: Kubernetes e Terraform"),
        AgentTurn(text=["<chiede conferma>", "<vuole salvare>"]),
        UserTurn(text="Sì, salva pure"),
        AgentTurn(text=["<conferma salvataggio>", "<saluta>", "<arrivederci>"], telephony_events=[EndCall()]),
    ]
    await ConversationRunner(hr_node, conv).run()

@pytest.mark.asyncio
async def test_fine_chiamata_esplicita(hr_node):
    conv = [
        UserTurn(text="No grazie, per ora è tutto. Arrivederci"),
        AgentTurn(text="*", telephony_events=[EndCall()]),
    ]
    await ConversationRunner(hr_node, conv).run()

@pytest.mark.asyncio
async def test_dati_opzionali(hr_node):
    conv = [
        UserTurn(text="Mario Rossi, DevOps, Kubernetes. La sua email è mario@rossi.it e il telefono è 333 1234567"),
        AgentTurn(text=["<conferma dati>", "<chiede conferma salvataggio>"]),
    ]
    await ConversationRunner(hr_node, conv).run()
