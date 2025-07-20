import os
from typing import List, Any, Optional

from langchain_ibm.chat_models import ChatWatsonx
from ibm_watsonx_ai.foundation_models.schema import TextChatParameters

parameters = TextChatParameters(
    max_tokens=1000,
    temperature=0.5,
    top_p=1,
    )

WX_API_KEY = os.getenv("WX_API_KEY")
WX_PROJECT_ID = os.getenv("WX_PROJECT_ID")


watsonx_llm = ChatWatsonx(
    model_id="meta-llama/llama-3-2-90b-vision-instruct",
    url="https://au-syd.ml.cloud.ibm.com",
    apikey=WX_API_KEY,
    project_id=WX_PROJECT_ID,
    params=parameters,
)

