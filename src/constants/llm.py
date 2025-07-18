import os
from typing import List, Any, Optional
from pydantic import Field
from src.react_agent.watsonx_config import PROJECT_ID

from langchain_ibm.chat_models import ChatWatsonx
from ibm_watsonx_ai.foundation_models.schema import TextChatParameters

parameters = TextChatParameters(
    max_tokens=100,
    temperature=0.5,
    top_p=1,
    )

watsonx_llm = ChatWatsonx(
    model_id="meta-llama/llama-3-3-70b-instruct",
    url="https://us-south.ml.cloud.ibm.com",
    apikey=os.getenv("WX_API_KEY"),
    project_id=os.getenv("WX_PROJECT_ID"),
    params=parameters,
)

