import os
from langchain_core.tools import tool, StructuredTool
from pydantic import BaseModel, Field

from .otp_utilities import OTPManager, EmailSender

# Note: It's important that every field has type hints. BaseTool is a
# Pydantic class and not having type hints can lead to unexpected behavior.

# Retrieve email credentials from environment variables
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_APP_PASSWORD")

if not SENDER_EMAIL or not SENDER_PASSWORD:
    raise ValueError("Email credentials not found in environment variables")

# SMTP server configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

otp_manager = OTPManager()

email_sender = EmailSender(
    SMTP_SERVER, SMTP_PORT, 
    SENDER_EMAIL, SENDER_PASSWORD
)

class SendOTPInput(BaseModel):
    email: str = Field(description="Email address to send OTP to")

def send_otp(email: str):
    "Sends an OTP to the specified email address for verification"
    otp = otp_manager.create_otp(email)
    if email_sender.send_otp_email(email, otp):
        return f"OTP sent successfully to {email}"
    return f"Failed to send OTP to {email}"

send_otp_tool = StructuredTool.from_function(
    name="send_otp_tool",
    func=send_otp, 
    input_schema=SendOTPInput, 
    description="Sends an OTP to the specified email address for verification"
)

class VerifyOTPInput(BaseModel):
    email: str = Field(description="Email address to verify OTP for")
    otp: str = Field(description="OTP to verify")

def verify_otp(email: str, otp: str):
    "Verifies the OTP provided by the user"
    if otp_manager.verify_otp(email, otp):
        return "OTP verified successfully"
    return "Invalid or expired OTP"

verify_otp_tool = StructuredTool.from_function(
    name="verify_otp_tool",
    func=verify_otp, 
    input_schema=VerifyOTPInput, 
    description="Verifies the OTP provided by the user"
)
