from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.constants.db import USER_REGISTRATION_DB_NAME
from src.dbio.models import Base

engine = create_engine(
    f"sqlite:///{USER_REGISTRATION_DB_NAME}"
)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
