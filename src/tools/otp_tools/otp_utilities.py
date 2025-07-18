
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Optional
from langchain.tools import BaseTool

class OTPManager:
    def __init__(self, expiry_minutes: int = 5):
        self.otps: Dict[str, Dict] = {}  # Store email -> {otp, expiry} mapping
        self.expiry_minutes = expiry_minutes
    
    def generate_otp(self, length: int = 6) -> str:
        """Generate a random OTP of specified length"""
        return ''.join(random.choices(string.digits, k=length))
    
    def create_otp(self, email: str) -> str:
        """Create and store OTP for an email"""
        otp = self.generate_otp()
        expiry = datetime.now() + timedelta(minutes=self.expiry_minutes)
        self.otps[email] = {"otp": otp, "expiry": expiry}
        return otp
    
    def verify_otp(self, email: str, otp: str) -> bool:
        """Verify if OTP is valid for the given email"""
        if email not in self.otps:
            return False
        
        stored_data = self.otps[email]
        if datetime.now() > stored_data["expiry"]:
            del self.otps[email]
            return False
            
        if stored_data["otp"] == otp:
            del self.otps[email]  # Remove OTP after successful verification
            return True
        return False

class EmailSender:
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
    
    def send_otp_email(self, to_email: str, otp: str) -> bool:
        """Send OTP via email"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.username
            msg['To'] = to_email
            msg['Subject'] = "Your OTP for Verification"
            
            body = f"Your OTP is: {otp}\nValid for 5 minutes."
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False

