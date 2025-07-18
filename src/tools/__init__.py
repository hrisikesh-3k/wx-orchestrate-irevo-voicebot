from langchain_core.tools import tool

from src.constants.llm import watsonx_llm
from src.tools.escalation_tool import escalate_to_voice_tool
from src.tools.watsonx_tool import search_faq_tool



@tool
def default_chat_tool(query: str) -> dict:
    """
    Respond to casual or social queries that do not require FAQ search or escalation,
    using the LLM to generate a natural response.
    """
    # Use the LLM to generate a conversational response
    response = watsonx_llm.invoke(query)
    # If the response is an AIMessage, extract content
    message = getattr(response, "content", str(response))
    return {
        "message": message,
        "show_escalation_buttons": False
    }