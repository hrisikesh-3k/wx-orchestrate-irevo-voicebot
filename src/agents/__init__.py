"""
Enhanced VoiceEscalationAgent with Response Formatting
Fixed escalation button logic and added better debugging
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
from src.logger import logger

from dotenv import load_dotenv
load_dotenv()

# Global session state tracking
session_escalation_states = {}


class ResponseFormatter:
    """Dedicated class for formatting agent responses with precise escalation logic"""
    
    def __init__(self):
        # Keywords that explicitly indicate escalation is needed
        self.explicit_escalation_phrases = [
            "connect you with",
            "let me connect",
            "talk to a human",
            "speak with an agent",
            "transfer you to",
            "escalate to",
            "human agent can help",
            "specialist can help",
            "representative can assist",
            "schedule a callback",
            "call you back"
        ]
        
        # Keywords that indicate user wants human help
        self.user_escalation_requests = [
            "talk to someone",
            "speak to a person", 
            "human agent",
            "representative",
            "real person",
            "customer service agent",
            "claim specialist",
            "talk to a manager"
        ]
        
        # Security issues that require human intervention
        self.security_escalation_triggers = [
            "account locked",
            "authentication failed",
            "fraud detected",
            "security breach",
            "access denied",
            "locked out"
        ]
    
    def format_response(self, raw_response: str, query: str) -> Dict:
        """Main formatting method with corrected escalation logic"""
        
        if not raw_response:
            return {
                "message": "I apologize, but I'm having trouble processing your request. Let me connect you with a human agent.",
                "show_escalation_buttons": True
            }
        
        # Clean the response text (minimal cleaning)
        cleaned = self.clean_text(raw_response)
        
        # Handle specific scenarios
        formatted = self.handle_specific_scenarios(cleaned, query)
        
        # Determine if escalation is needed with corrected logic
        should_escalate = self.should_escalate(formatted, query)
        
        return {
            "message": formatted,
            "show_escalation_buttons": should_escalate
        }
    
    def clean_text(self, text: str) -> str:
        """Minimal cleaning to preserve content"""
        
        if not text:
            return ""
        
        # Remove markdown formatting
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\|[^|]*\|', '', text)
        
        # Clean up whitespace
        text = re.sub(r'\n+', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def handle_specific_scenarios(self, text: str, query: str) -> str:
        """Handle specific scenarios - keep original response for claim info"""
        
        # For claim-related queries, keep the response as-is
        claim_keywords = ["claim", "policy", "coverage", "benefit", "member id"]
        if any(keyword in query.lower() for keyword in claim_keywords):
            return text
        
        # Only modify for non-claim responses
        return text
    
    def should_escalate(self, response: str, query: str) -> bool:
        """Precise escalation logic - only escalate when actually needed"""
        
        if not response:
            return True
        
        response_lower = response.lower()
        query_lower = query.lower()
        
        # 1. EXPLICIT ESCALATION: Response explicitly mentions connecting to human
        for phrase in self.explicit_escalation_phrases:
            if phrase in response_lower:
                return True
        
        # 2. USER REQUESTS: User explicitly asks for human help
        for phrase in self.user_escalation_requests:
            if phrase in query_lower:
                return True
        
        # 3. SECURITY ISSUES: Security problems that need human intervention  
        for phrase in self.security_escalation_triggers:
            if phrase in response_lower or phrase in query_lower:
                return True
        
        # 4. SYSTEM ERRORS: Response indicates system issues
        error_indicators = [
            "technical difficulty",
            "system error", 
            "unable to access",
            "having trouble",
            "connection error"
        ]
        for indicator in error_indicators:
            if indicator in response_lower:
                return True
        
        # 5. INCOMPLETE RESPONSES: Only if response is genuinely too short
        if len(response.strip()) < 10:
            return True
        
        # 6. CLAIM-SPECIFIC: For claim responses, only escalate if there's a problem
        if "claim" in response_lower:
            # These indicate successful claim information - NO escalation
            success_indicators = [
                "processed",
                "approved", 
                "paid",
                "completed",
                "explanation of benefits",
                "claim has been",
                "insurance has paid"
            ]
            
            # If response contains claim info AND success indicators, don't escalate
            if any(indicator in response_lower for indicator in success_indicators):
                return False
            
            # Only escalate for claim issues like denied, pending investigation, etc.
            problem_indicators = [
                "denied",
                "rejected", 
                "under investigation",
                "additional information needed",
                "contact us",
                "call us"
            ]
            
            if any(indicator in response_lower for indicator in problem_indicators):
                return True
        
        # 7. DEFAULT: If none of the escalation conditions are met, don't escalate
        return False


class VoiceEscalationAgent:
    def __init__(self):
        self.llm = watsonx_llm 
        self.tools = [search_faq_tool, escalate_to_voice_tool, default_chat_tool]
        self.memory_manager = MemoryManager()
        
        # Initialize response formatter with corrected logic
        self.formatter = ResponseFormatter()
        
        # Create custom prompt
        self.prompt = self.create_custom_prompt()
        
        # Create the base agent with tools
        self.agent = self.initialize_agent()

    def create_custom_prompt(self):
        """Create a custom prompt template"""
        
        ENHANCED_AGENT_PROMPT = f"""{SYSTEM_PROMPT}

RESPONSE FORMAT GUIDELINES:
- Provide complete, helpful responses for insurance queries
- For claim status requests, give all available information clearly
- Only suggest escalation when you cannot help or when explicitly requested
- Keep responses conversational and professional

Remember: Only escalate to human agents when truly necessary."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", ENHANCED_AGENT_PROMPT),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad")
        ])
        return prompt

    def initialize_agent(self):
        try:
            agent = create_tool_calling_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=self.prompt,
            )
            
            agent_executor = AgentExecutor(
                agent=agent, 
                tools=self.tools, 
                verbose=True,
                handle_parsing_errors=True,
                max_iterations=5,
                max_execution_time=60,
                return_intermediate_steps=False,
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
            processed_query = self.preprocess_query(query)
            
            response = self.agent.invoke(
                {"input": processed_query},
                config={"configurable": {"session_id": session_id}},
            )
            
            logger.info(f"Raw agent response: {response}")

            # Extract message text
            message_text = self.extract_message_text(response)

            # Format the response
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
    
    def extract_message_text(self, response) -> str:
        """Extract message text from agent response"""
        
        if not response:
            return ""
        
        if isinstance(response, dict):
            return (response.get("output") or 
                   response.get("message") or 
                   response.get("content") or
                   str(response))
        else:
            return str(response)

    def preprocess_query(self, query: str) -> str:
        """Preprocess query"""
        query = query.strip()
        
        # Explicit human requests
        human_requests = ["human", "person", "agent", "representative", "talk to someone"]
        if any(word in query.lower() for word in human_requests):
            return f"{query} [ESCALATION_NEEDED]"
        
        return query

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