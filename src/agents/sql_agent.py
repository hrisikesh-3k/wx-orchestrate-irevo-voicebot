from langchain_community.utilities import SQLDatabase
from src.constants import DATABASE_NAME, SQLITE_URL, RENT_TABLE_NAME, LEASE_TABLE_NAME
from src.constants.llm import llm
from langchain_community.agent_toolkits import create_sql_agent




class SqlAgent:
    db = None
    sql_agent= None
    def __init__(self):
        if not SqlAgent.db:
            SqlAgent.db = SQLDatabase.from_uri(SQLITE_URL)
            
        
        
        
    @staticmethod
    def check_connection():
        print(SqlAgent.db.dialect)
        print(SqlAgent.db.get_usable_table_names())
        return SqlAgent.db.run(f"SELECT * FROM {RENT_TABLE_NAME} LIMIT 10;")
    
    def get_sql_agent(self):
        if not self.sql_agent:
            self.sql_agent = create_sql_agent(llm, db=self.db, agent_type="openai-tools", verbose=True)
        return self.sql_agent