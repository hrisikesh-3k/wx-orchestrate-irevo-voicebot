from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from pydantic.v1 import BaseModel, Field
from langchain_core.messages import BaseMessage, HumanMessage
from src.constants.llm import watsonx_llm  # Your WatsonX LLM

# Define the output schema using Pydantic
class SummaryOutput(BaseModel):
    name: str = Field(description="User's name from the conversation, or null if not provided")
    policy_number: str = Field(description="User's policy number from the conversation, or null if not provided")
    summary: str = Field(description="2-3 line summary of the entire conversation")

def format_message_history(messages: List[BaseMessage]) -> str:
    """Convert LangChain message objects to formatted string"""
    formatted_messages = []
    for message in messages:
        if hasattr(message, 'type'):
            role = "User" if message.type == "human" else "Assistant"
        else:
            role = "User" if message.__class__.__name__ == "HumanMessage" else "Assistant"
        formatted_messages.append(f"{role}: {message.content}")
    return "\n".join(formatted_messages)

# Create the prompt template
summary_prompt = ChatPromptTemplate.from_template("""
Given the following conversation history between a user and an assistant, extract the user's **name** and **policy number** (if provided), and then summarize the entire conversation in 2-3 lines.

If name or policy number is not provided, return null for those fields.

Return the result in JSON format like:
{{
  "name": "...",
  "policy_number": "...",
  "summary": "..."
}}

Conversation History:
{chat_history}
""")

# Create the output parser
output_parser = JsonOutputParser(pydantic_object=SummaryOutput)

# Create the runnable chain using LCEL (LangChain Expression Language)
summary_chain = summary_prompt | watsonx_llm | output_parser

# Alternative: If you want to add the format instructions to the prompt
summary_prompt_with_format = ChatPromptTemplate.from_template("""
Given the following conversation history between a user and an assistant, extract the user's **name** and **policy number** (if provided), and then summarize the entire conversation in 2-3 lines.

If name or policy number is not provided, return null for those fields.

{format_instructions}

Conversation History:
{chat_history}
""").partial(format_instructions=output_parser.get_format_instructions())

# Chain with format instructions
summary_chain_with_format = summary_prompt_with_format | watsonx_llm | output_parser

# Usage examples updated for message objects:
async def run_summary_async(messages: List[BaseMessage]):
    """Run the chain asynchronously with message objects"""
    chat_history = format_message_history(messages)
    result = await summary_chain.ainvoke({"chat_history": chat_history})
    return result

def run_summary_sync(messages: List[BaseMessage]):
    """Run the chain synchronously with message objects"""
    chat_history = format_message_history(messages)
    result = summary_chain.invoke({"chat_history": chat_history})
    print(f"Summary result: {result}")
    return result

# For streaming (if your LLM supports it):
def run_summary_stream(messages: List[BaseMessage]):
    """Stream the response with message objects"""
    chat_history = format_message_history(messages)
    for chunk in summary_chain.stream({"chat_history": chat_history}):
        yield chunk

# For batch processing multiple conversations:
def run_summary_batch(message_lists: List[List[BaseMessage]]):
    """Process multiple conversations in batch"""
    inputs = [{"chat_history": format_message_history(messages)} for messages in message_lists]
    results = summary_chain.batch(inputs)
    return results

