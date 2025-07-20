import os, sys
from typing import Any, Dict, Optional
from langchain_core.tools import tool
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fpdf import FPDF
from src.constants import *
import re
from pydantic import BaseModel, Field
from langchain_core.tools.structured import StructuredTool

from src.agents.wxorc_agent import OrchestrateClient

from src.logger import logger


@tool
def search_faq_tool(query: str) -> Dict[str, Any]:
    """
    Search the FAQ database using Watson X Orchestrate RAG agent for insurance-related queries.
    
    This tool should be used when:
    - User asks about policy claim status or claim procedures
    - User needs information about insurance products, coverage, or benefits
    - User asks about insurance policies, procedures, or regulations
    - User has technical questions about insurance features or functionality
    - User asks "how to" questions related to insurance operations
    - User needs clarification on policy terms or coverage details
    
    Do NOT use this tool when:
    - User is just greeting or making small talk
    - User is expressing frustration or explicitly asking for human help
    - User reports outdated/incorrect claim status information
    - User is making complaints or expressing dissatisfaction with claim handling
    - User needs immediate claim resolution or complex account-specific issues
    
    Args:
        query (str): The user's insurance question or search term. Should be a clear, 
                    specific question or keywords related to insurance. Examples:
                    - "I want to check the status of my claim"
                    - "What documents do I need for a car insurance claim?"
                    - "How long does claim processing take?"
                    - "What is covered under my policy?"
    
    Returns:
        Dict[str, Any]: A dictionary containing:
            - message (str): The FAQ answer or escalation message
            - show_escalation_buttons (bool): Whether to show voice escalation options
            - escalation_reason (str, optional): Reason for escalation if applicable
    
    Raises:
        Exception: If Watson X Orchestrate API call fails, automatically escalates to human agent
    
    Edge Cases Handled:
        - Empty or invalid query: Prompts user for clarification
        - No results found: Escalates to human agent with explanation
        - API/system errors: Gracefully escalates to human support
        - Timeout errors: Falls back to human agent escalation
    """
    try:
        logger.info(f"Searching FAQ database via Watson X Orchestrate for: {query}")
        
        # Handle empty or invalid queries
        if not query or not query.strip():
            logger.warning("Empty query received")
            return {
                "message": "I'd be happy to help! Could you please tell me what specific insurance question you have?",
                "show_escalation_buttons": False
            }
        
        # Invoke Watson X Orchestrate RAG agent
        search_result = invoke_watsonx_rag_agent(query.strip())
        logger.info(f"Watson X RAG search completed: {search_result is not None}")
        
        # Handle no results found
        if not search_result:
            logger.info("No FAQ result found from Watson X, suggesting escalation")
            return {
                "message": "I couldn't find specific information about that in our knowledge base. Let me connect you with our claim specialist who can help.",
                "show_escalation_buttons": True,
                "escalation_reason": "no_faq_results"
            }
        
        
        
        # Return successful FAQ result
        
        response = {
            "message": search_result,
            "show_escalation_buttons": False
        }
        logger.info(f"FAQ search result from tool: {response['message']}")

        return response

    except TimeoutError as e:
        logger.error(f"Watson X Orchestrate timeout: {e}")
        return {
            "message": "I'm experiencing a delay accessing our knowledge base. Let me connect you with a human agent for immediate assistance.",
            "show_escalation_buttons": True,
            "escalation_reason": "api_timeout"
        }
        
    except ConnectionError as e:
        logger.error(f"Watson X Orchestrate connection error: {e}")
        return {
            "message": "I'm having trouble connecting to our knowledge base. Let me get you connected with a human agent.",
            "show_escalation_buttons": True,
            "escalation_reason": "connection_error"
        }
        
    except Exception as e:
        logger.error(f"Error in search_faq_tool with Watson X Orchestrate: {e}")
        return {
            "message": "I'm having trouble accessing that information right now. Let me connect you with our claim specialist who can help.",
            "show_escalation_buttons": True,
            "escalation_reason": "system_error"
        }


def invoke_watsonx_rag_agent(query: str) -> str:
    """
    Invoke Watson X Orchestrate RAG agent for FAQ search.
    
    Args:
        query (str): The search query
        
    Returns:
        str: The RAG response from Watson X Orchestrate
        
    Raises:
        TimeoutError: If the API call times out
        ConnectionError: If connection to Watson X fails
        Exception: For other API-related errors
    """
    
    client = OrchestrateClient()
    wx_response = client.ask(query)
    
    logger.info(f"Watson X Orchestrate response: {wx_response}")

    return wx_response



    