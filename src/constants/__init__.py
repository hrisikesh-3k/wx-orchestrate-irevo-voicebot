# constants.py
"""
Configuration constants for the iRevo Voice Agent Integration
"""

CHATBOT_NAME = "ClaimBuddy"

# LLM Configuration
import os
ROOT_DIR = os.getcwd()

OPENAI_MODEL_NAME = "gpt-4o-mini"  # or "mixtral-8x7b-32768" based on your preference


# PDF Processing
PDF_FOLDER_PATH = "data"  # Local folder containing PDF files
PDF_PATH = os.path.join(ROOT_DIR, PDF_FOLDER_PATH, "Insurance_Claim_FAQ_Voice_Escalation.pdf")  # Path to the PDF file
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

# Agent Configuration
AGENT_NAME = "Insurance Agent"

AGENT_DESCRIPTION = """
You are a helpful bank support agent. You help customers with their banking queries. 
You can answer questions about account issues, transactions, and general banking information. 
You have access to a knowledge base of frequently asked questions (FAQs) and can search it for answers.
You can also escalate issues to human voice support if the customer is dissatisfied or requests it.
When you detect customer dissatisfaction, escalation requests, or issues you cannot resolve,
you should escalate to voice support. Otherwise, use RAG to provide helpful answers.
"""

# Escalation Keywords and Patterns
ESCALATION_KEYWORDS = [
    "talk to agent", "human agent", "live agent", "speak to someone",
    "escalate", "manager", "supervisor", "executive", "representative",
    "not working", "still not working", "doesn't work", "can't access",
    "frustrated", "angry", "disappointed", "dissatisfied", "unhappy",
    "this is not helping", "useless", "waste of time", "connect me to"
]

# System Messages
ESCALATION_MESSAGE = """
I understand you're experiencing difficulties and our automated solutions haven't resolved your issue. 
Let me connect you with a human support agent who can provide personalized assistance.
"""

WELCOME_MESSAGE = """
Hello! I'm your Insurance Claim support assistant. I'm here to help you with your insurance claim related queries.
How can I assist you today?
"""