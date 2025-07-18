"""
Enhanced VoiceEscalationAgent with Response Formatting
Fixes formatting issues while maintaining existing functionality
"""

import os
import logging
import re
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.runnables import RunnableWithMessageHistory


from src.constants.llm import watsonx_llm

from langchain_core.runnables.history import RunnableWithMessageHistory

from src.constants import *
from src.prompts import SYSTEM_PROMPT
from src.agents.memory import MemoryManager
from src.tools import escalate_to_voice_tool, search_faq_tool, default_chat_tool

from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global session state tracking
session_escalation_states = {}


class ResponseFormatter:
    """Dedicated class for formatting agent responses for better UI display"""
    
    def __init__(self):
        self.security_keywords = [
            "locked", "lockout", "authentication", "fraud", "blocked", 
            "security", "access denied", "failed attempts", "temporarily locked"
        ]
        self.escalation_keywords = [
            "human agent", "representative", "escalate", "connect you",
            "talk to someone", "specialist", "support team"
        ]
    
    def format_response(self, raw_response: str, query: str) -> Dict:
        """Main formatting method that cleans and enhances responses"""
        
        # Step 1: Clean the response text
        cleaned = self.clean_text(raw_response)
        
        # Step 2: Handle specific scenarios
        formatted = self.handle_specific_scenarios(cleaned, query)
        
        # Step 3: Determine if escalation is needed
        should_escalate = self.needs_escalation(formatted, query)
        
        return {
            "message": formatted,
            "show_escalation_buttons": should_escalate
        }
    
    def clean_text(self, text: str) -> str:
        """Remove problematic formatting and duplicates"""
        
        # Remove duplicate sentences (common issue in your output)
        text = self.remove_duplicates(text)
        
        # Remove markdown tables
        text = re.sub(r'\|[^|]*\|[^|]*\|[^|]*\|', '', text, flags=re.MULTILINE)
        text = re.sub(r'\|---\|---\|---\|', '', text)
        
        # Remove bullet points with formatting
        text = re.sub(r'- \*\*([^*]+)\*\*:', r'\1:', text)
        
        # Remove bold formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        
        # Remove "Here's a simple table to summarize:" type phrases
        text = re.sub(r'Here\'s a simple table to summarize:.*?(?=\n|$)', '', text, flags=re.IGNORECASE)
        
        # Clean up whitespace
        text = re.sub(r'\n+', '\n', text)
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def remove_duplicates(self, text: str) -> str:
        """Remove duplicate content that appears in agent responses"""
        
        # Split by sentences
        sentences = re.split(r'[.!?]+', text)
        seen = set()
        unique_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 10:  # Ignore very short fragments
                # Create a normalized version for comparison
                normalized = re.sub(r'[^a-zA-Z0-9\s]', '', sentence.lower())
                if normalized not in seen:
                    seen.add(normalized)
                    unique_sentences.append(sentence)
        
        return '. '.join(unique_sentences) + '.' if unique_sentences else text
    
    def handle_specific_scenarios(self, text: str, query: str) -> str:
        """Handle specific banking scenarios with better responses"""
        
        # Authentication/lockout scenarios
        if any(keyword in query.lower() for keyword in self.security_keywords):
            return self.format_authentication_response(text)
        
        # General banking questions
        if any(word in query.lower() for word in ["account", "balance", "transaction", "fee"]):
            return self.format_banking_response(text)
        
        # Return cleaned text for other scenarios
        return text
    
    def format_authentication_response(self, text: str) -> str:
        """Format authentication/lockout related responses"""
        
        return """I understand you're having trouble with authentication. After 3 failed login attempts, your account gets temporarily locked for security reasons.

I can help you get this resolved quickly by connecting you with one of our security specialists who can unlock your account and verify your identity. Would you like me to arrange that for you?"""
    
    def format_banking_response(self, text: str) -> str:
        """Format general banking responses to be more conversational"""
        
        # Keep the original response but make it more conversational
        if "Based on the provided document" in text:
            text = re.sub(r'Based on the provided document,?\s*', '', text, flags=re.IGNORECASE)
        
        # Remove formal language patterns
        text = re.sub(r'here\'s the relevant information regarding', 'regarding', text, flags=re.IGNORECASE)
        
        return text
    
    def needs_escalation(self, response: str, query: str) -> bool:
        """Determine if escalation buttons should be shown"""
        
        # Security-related issues should trigger escalation
        if any(keyword in query.lower() or keyword in response.lower() 
               for keyword in self.security_keywords):
            return True
        
        # If response mentions connecting to human
        if any(keyword in response.lower() for keyword in self.escalation_keywords):
            return True
        
        # If customer explicitly asks for human help
        human_requests = ["human", "person", "agent", "representative", "talk to someone"]
        if any(word in query.lower() for word in human_requests):
            return True
        
        return False


class VoiceEscalationAgent:
    def __init__(self):
        self.llm = watsonx_llm 
        self.tools = [search_faq_tool, escalate_to_voice_tool, default_chat_tool]
        self.memory_manager = MemoryManager()
        
        # Initialize response formatter
        self.formatter = ResponseFormatter()
        
        # Create custom prompt instead of using HUB_PROMPT
        self.prompt = self.create_custom_prompt()
        
        # Create the base agent with tools
        self.agent = self.initialize_agent()

    def create_custom_prompt(self):
        """Create a custom prompt template for better control"""
        
        # Enhanced prompt with formatting guidelines
        ENHANCED_AGENT_PROMPT = f"""{SYSTEM_PROMPT}

RESPONSE FORMAT GUIDELINES:
- Keep responses concise and conversational
- Avoid creating tables, excessive bullet points, or complex formatting
- Don't repeat information multiple times
- Use simple, clear language that works well in chat interfaces
- For account security issues, be empathetic and offer to connect with specialists

Remember: Your responses will be displayed in a chat interface, so keep them clean and user-friendly."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", ENHANCED_AGENT_PROMPT),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad")
        ])
        return prompt

    def initialize_agent(self):
        try:
            # Initialize the agent with the custom prompt and tools
            agent = create_tool_calling_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=self.prompt,  # Use custom prompt instead of HUB_PROMPT
            )
            
            agent_executor = AgentExecutor(
                agent=agent, 
                tools=self.tools, 
                verbose=True,
                handle_parsing_errors=True,  # Add error handling
                # max_iterations=3,  # Prevent infinite loops
                # early_stopping_method="generate"  # Stop early if needed
            )
            
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
            # Add some preprocessing to help guide the agent
            processed_query = self.preprocess_query(query)
            
            #orchestrate agent invocation 
            
            
            response = self.agent.invoke(
                {"input": processed_query},
                config={"configurable": {"session_id": session_id}},
            )
            
            logger.debug(f"Raw agent response: {response}")

            # Extract message text
            message_text = None
            if isinstance(response, dict):
                message_text = response.get("output") or response.get("message") or str(response)
            else:
                message_text = str(response)

            # NEW: Format the response for better UI display
            formatted_response = self.formatter.format_response(message_text, query)

            return {
                "message": formatted_response["message"],
                "show_escalation_buttons": formatted_response["show_escalation_buttons"],
                "session_id": session_id
            }

        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return {
                "message": "I apologize for the technical difficulty. Let me connect you with a human agent who can help you right away.",
                "show_escalation_buttons": True,
                "escalation_reason": "agent_error",
                "session_id": session_id
            }

    def preprocess_query(self, query: str) -> str:
        """Add context hints to help guide tool usage"""
        query = query.strip()
        
        # Simple greetings - add hint to respond directly
        simple_greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "how are you"]
        if query.lower() in simple_greetings:
            return f"{query}"  # Keep as is, let prompt handle it
        
        # Explicit human requests - add urgency
        human_requests = ["human", "person", "agent", "representative", "talk to someone"]
        if any(word in query.lower() for word in human_requests):
            return f"{query} [ESCALATION_NEEDED]"
        
        return query

    def detect_escalation_intent(self, message_text: str) -> bool:
        """Detect if the response indicates escalation is needed"""
        escalation_indicators = [
            "talk to them now",
            "schedule a callback", 
            "connecting you to a human",
            "escalate",
            "human agent",
            "representative",
            "transfer you",
            "connect you with"
        ]
        
        return any(indicator in message_text.lower() for indicator in escalation_indicators)

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