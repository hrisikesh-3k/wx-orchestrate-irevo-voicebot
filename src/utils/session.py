from collections import namedtuple
import uuid

# Define the namedtuple
UserSession = namedtuple("UserSession", ["session_id"])

# Function to generate and return a namedtuple instance
def get_user_session():
    return UserSession(session_id=str(uuid.uuid4()))
