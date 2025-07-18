# agent.py
"""
Optimized LangChain Tool-Calling Agent for Bank Support with Voice Escalation
Smart agent that uses logical reasoning to determine when to use tools
"""

import os
import logging
from typing import Dict, Generator, Optional, Any
from langchain_core.prompts import PromptTemplate
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.tools import tool
from langchain.memory import ConversationBufferWindowMemory
from langchain_openai.chat_models import ChatOpenAI
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_core.runnables.history import RunnableWithMessageHistory

from src.rag import search_faq_database
from src.constants import *
from src.react_agent.output_parser import EscalationOutputParser
from src.react_agent.prompt import AGENT_PROMPT, HUB_PROMPT
from src.react_agent.memory import MemoryManager
from src.react_agent.tools import search_faq_tool, escalate_to_voice

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global session state tracking
session_escalation_states = {}


class VoiceEscalationAgent:
    def __init__(self):
        self.llm = 
        self.tools = [search_faq_tool, escalate_to_voice]
        self.memory_manager = MemoryManager()

        # Create the base agent with tools
        self.agent = self.initialize_agent()

        
    def initialize_agent(self):
        try:
            # Initialize the agent with the prompt and tools
            agent = create_tool_calling_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=HUB_PROMPT,
            )
            
            agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)
            
            agent_with_chat_history = RunnableWithMessageHistory(
                agent_executor,
                get_session_history=self.memory_manager.get,
                input_messages_key="input",
                history_messages_key="chat_history",
            )

            logger.info("VoiceEscalationAgent initialized successfully")
            
            return agent_with_chat_history

        except Exception as e:
            logger.error(f"Failed to initialize VoiceEscalationAgent: {e}")
            raise 

    def chat(self, query: str, session_id: str) -> dict:
        try:
            response = self.agent.invoke(
                {"input": query},
                config={"configurable": {"session_id": session_id}},
            )
            logger.debug(f"Raw agent response: {response}")

            message_text = None
            if isinstance(response, dict):
                message_text = response.get("output") or response.get("message") or str(response)
            else:
                message_text = str(response)

            # Detect if escalation message is present
            should_escalate = (
                "talk to them now" in message_text.lower() or
                "schedule a callback" in message_text.lower() or
                "connecting you to a human" in message_text.lower()
            )

            return {
                "message": message_text,
                "show_escalation_buttons": should_escalate,
                "session_id": session_id
            }

        except Exception as e:
            return {
                "message": f"Something went wrong: {str(e)}",
                "show_escalation_buttons": True,
                "escalation_reason": "agent_error",
                "session_id": session_id
            }



    def reset_conversation(self, session_id: str):
        self.memory_manager.reset(session_id)

    def cleanup_session(self, session_id: str):
        self.memory_manager.cleanup(session_id)

    def get_conversation_history(self, session_id: str):
        return self.memory_manager.get(session_id).messages

    def get_active_sessions(self):
        return self.memory_manager.list_sessions()

    def is_escalated(self, session_id: str) -> bool:
        return False

    def mark_session_transferred(self, session_id: str, target_agent: str):
        pass