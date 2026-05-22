import os

import anthropic
from chat_node import HrChatNode
from config import INITIAL_MESSAGE, SYSTEM_PROMPT
from loguru import logger

from line import Bridge, CallRequest, VoiceAgentApp, VoiceAgentSystem
from line.events import AgentSpeechSent, UserStartedSpeaking, UserStoppedSpeaking, UserTranscriptionReceived

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
anthropic_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


async def handle_new_call(system: VoiceAgentSystem, call_request: CallRequest):
    logger.info(f"Nuova chiamata HR: {call_request.call_id}")

    conversation_node = HrChatNode(
        system_prompt=call_request.agent.system_prompt or SYSTEM_PROMPT,
        anthropic_client=anthropic_client,
    )
    conversation_bridge = Bridge(conversation_node)
    system.with_speaking_node(conversation_node, bridge=conversation_bridge)

    conversation_bridge.on(UserTranscriptionReceived).map(conversation_node.add_event)
    conversation_bridge.on(AgentSpeechSent).map(conversation_node.add_event)
    (
        conversation_bridge.on(UserStoppedSpeaking)
        .interrupt_on(UserStartedSpeaking, handler=conversation_node.on_interrupt_generate)
        .stream(conversation_node.generate)
        .broadcast()
    )

    await system.start()

    introduction = call_request.agent.introduction
    await system.send_initial_message(INITIAL_MESSAGE if introduction is None else introduction)
    await system.wait_for_shutdown()


app = VoiceAgentApp(handle_new_call)

if __name__ == "__main__":
    app.run()
