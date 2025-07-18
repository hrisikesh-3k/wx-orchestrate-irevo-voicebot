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
import logging
from pydantic import BaseModel, Field
from langchain_core.tools.structured import StructuredTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@tool
def escalate_to_voice(reason: str) -> Dict[str, Any]:
    """
    Escalate the issue to a human voice support agent. 
    Use this tool when:
    - User explicitly requests to speak with a human/agent/person
    - User expresses frustration or dissatisfaction
    - User needs help with complex issues beyond FAQ scope
    
    Args:
        reason: The reason for escalation
        
    Returns:
        Dict containing escalation message and flag
    """
    try:
        logger.info(f"Escalation triggered. Reason: {reason}")
        return {
            "message": (
                "I'm connecting you to a human support agent who can better assist you. "
                "You can talk to them now or schedule a callback using the options below."
            ),
            "show_escalation_buttons": True,
            "escalation_reason": reason
        }
    except Exception as e:
        logger.error(f"Error in escalate_to_voice: {e}")
        return {
            "message": "I'm connecting you to a human support agent.",
            "show_escalation_buttons": True,
            "escalation_reason": "system_error"
        }