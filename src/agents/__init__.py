from src.tools import (#format_phone_number, sql_agent_tool,
                       generate_lease_agreement_tool,
                       agreement_and_payment_mailer_tool,
                       calculate_offer_tool,
                       format_phone_number_tool)
from src.tools.otp_tools import send_otp_tool, verify_otp_tool

from src.tools.new_tools import (
    get_lease_details_tool,
    verify_tenant_apartment_tool,
    check_rent_status_tool,
    get_tenant_email_tool,
    verify_phone_tool,
    verify_tenant_tool,
    
)
from src.prompts import SYSTEM_PROMPT
from src.prompts.prompt_otp import SYSTEM_PROMPT_WITH_OTP
from src.constants.llm import llm 

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.memory import ConversationBufferMemory

from langchain_core.caches import InMemoryCache
from langchain_core.globals import set_llm_cache

set_llm_cache(InMemoryCache())

memory = ConversationBufferMemory(memory_key="chat_history",
                                  return_messages=True) #mongodb is planned as memory


class RealEstateAgent:  
    
    def __init__(self):
        pass
    
    
    def get_prompt(self):
        prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT_WITH_OTP),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad")
    ])
        
        return prompt
    
    def build_agent(self)-> AgentExecutor:
        
        prompt = self.get_prompt()
        
        
        
        tools = [ #sql_agent_tool,
                 generate_lease_agreement_tool,
                 agreement_and_payment_mailer_tool,
                 send_otp_tool,
                 verify_otp_tool,
                 format_phone_number_tool,
                 calculate_offer_tool
                 ]
        new_tools = [get_lease_details_tool,
                    verify_tenant_apartment_tool,
                    check_rent_status_tool,
                    get_tenant_email_tool,
                    verify_phone_tool,
                    verify_tenant_tool
                    ]
        tools.extend(new_tools)
        
        
        agent = create_tool_calling_agent(llm, 
                                          tools, 
                                          prompt)
        
        agent_executor = AgentExecutor(
            agent=agent, 
            tools=tools,
            verbose=True,
            memory=memory  # You might want to add memory here
        )
        
        return agent_executor