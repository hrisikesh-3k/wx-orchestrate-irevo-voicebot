from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class UserVerification(Base):
    __tablename__ = "user_verification"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    policy_number = Column(String, unique=True, nullable=False)
