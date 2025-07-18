## tools
import os, sys
from typing import Optional
from langchain_core.tools import tool
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from fpdf import FPDF
from src.constants import *
# from src.agents.sql_agent import SqlAgent
import re
from pydantic import BaseModel, Field
from langchain_core.tools.structured import StructuredTool
# sql_agent_getter = SqlAgent()
# sql_agent = sql_agent_getter.get_sql_agent()

def format_as_points(text):
    """
    Converts a text into numbered points by splitting at each condition or clause.

    Args:
        text (str): The input text containing terms and conditions.

    Returns:
        str: A string formatted as numbered points.
    """
    # Split the text into clauses based on commas, semicolons, or periods.
    clauses = [clause.strip() for clause in text.replace('\n', '').split(',') if clause.strip()]

    # Format each clause as a numbered point.
    points = "\n".join(f"{i+1}. {clause}" for i, clause in enumerate(clauses))

    return points        
        
@tool
def sql_agent_tool(input):
    """Use this tool to interact with the SQLite database to retrieve tenant and lease data.
    This tool could be used to do all the database related activities including CRUD. 

    """
    # return sql_agent.invoke({"input": input})
    return "SQL Agent Tool is not implemented yet."

class GenerateLeaseAgreementInput(BaseModel):
    tenant_name: str = Field(description="Name of the tenant")
    apartment_number: str = Field(description="Apartment number")
    tenant_email: str = Field(description="Email address of the tenant")
    tenant_phone: str = Field(description="Phone number of the tenant")
    owner_name: str = Field(description="Name of the property owner")
    owner_email: str = Field(description="Email address of the property owner")
    owner_contact: str = Field(description="Contact number of the property owner")
    property_name: str = Field(description="Name of the property")
    city: str = Field(description="City where the property is located")
    zip_code: str = Field(description="Zip code of the property")
    lease_start: str = Field(description="Start date of the new lease. Date would be current date or date when the previous lease gonna expire.")
    lease_end: str = Field(description="End date of the new lease. Date would be 1 year from lease_start.")
    rent_amount: str = Field(description="Monthly rent amount for new lease")
    lease_terms_conditions: str = Field(description="Terms and conditions of the lease")
    renewal_terms_conditions: str = Field(description="Terms and conditions for lease renewal")
    
    
# @tool(parse_docstring=True, 
#       args_schema=GenerateLeaseAgreementInput,
#       error_on_invalid_docstring=False)

def generate_lease_agreement(
    tenant_name: str, 
    apartment_number: str, 
    tenant_email: str, 
    tenant_phone: str, 
    owner_name: str, 
    owner_email: str, 
    owner_contact: str, 
    property_name: str, 
    city: str, 
    zip_code: str, 
    lease_start: str, 
    lease_end: str, 
    rent_amount: str,
    lease_terms_conditions:str,
    renewal_terms_conditions:str
    ) -> str:
    
        
    try:
        

        agreement = f"""
        LEASE AGREEMENT
        Tenant Name: {tenant_name}
        Tenant Apartment: {apartment_number}
        Tenant Email: {tenant_email}
        Tenant Contact: {tenant_phone}

        Owner Name: {owner_name}
        Owner Email: {owner_email}
        Owner Contact: {owner_contact}

        Property: {property_name}
        Property City: {city}
        Property Zip Code: {zip_code}

        Basic Terms and Conditions:
        1. Lease Term: Start Date: {lease_start}, End Date: {lease_end}
        2. Rent: ${rent_amount} per month, due on the 5th of each month. Payment methods include cheque or online payment.
        3. Security Deposit: A security deposit of ${rent_amount} is required and refundable subject to property condition.
        4. Maintenance and Repairs: Tenant handles minor repairs; landlord handles major repairs unless caused by tenant negligence.
        5. Utilities: Tenant pays for electricity, water, and gas.
        6. Default: Landlord may terminate the lease and seek damages for breaches or non-payment of rent.
        7. Governing Law: This lease is governed by the laws of the property location.

        Lease Terms and Conditions:
        {lease_terms_conditions}
        
        Renewal Terms:
        {format_as_points(renewal_terms_conditions)}

        Signed By:
        Tenant Signature: _____________________   Date: ___________
        Owner Signature: ______________________   Date: ___________
        """
        
        # Initialize PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        # Add content to the PDF
        for line in agreement.strip().split("\n"):
            pdf.cell(200, 10, txt=line.strip(), ln=True)

        # Define file path
        file_name = f"Lease_Agreement_{tenant_name.replace(' ', '_')}.pdf"
        file_path = os.path.join("generated_leases", file_name)
        
        # Ensure the directory exists
        os.makedirs("generated_leases", exist_ok=True)

        # Save PDF
        pdf.output(file_path)

        return file_path
    except Exception as e:
        return f"Error generating lease agreement: {str(e)}"
    

generate_lease_agreement_tool = StructuredTool.from_function(
    name="generate_lease_agreement_tool",
    func =generate_lease_agreement,
    input_schema=GenerateLeaseAgreementInput,
    description="Generates a lease agreement PDF for a tenant and owner with specified details."

)
    
class AgreementAndRentPaymentMailerInput(BaseModel):
    tenant_first_name: str = Field(description="First name of the tenant")
    recipient_email: str = Field(description="Email address of the recipient")
    attachment_path: Optional[str] = Field(description="Path to the Lease agreement pdf attachment file")
    include_payment_link: bool = Field(description="Whether to include a payment link. True if the chat is about rent payment. \
                                       False if the chat is about lease renewal.")

def agreement_and_payment_mailer(
    tenant_first_name:str,
    recipient_email: str,
    attachment_path: Optional[str] = None,
    include_payment_link: bool = False,
) -> str:
    
    
    """Send an email with optional attachment and payment link. 
    Find out the recipient/tenant mail id from the database or previous chats.
    The email is sensitive so make sure you send the mail to the correct recipient.

    Args:
        tenant_first_name: First name of the tenant
        recipient_email: Email address of the recipient
        attachment_path: Path to the Lease agreement pdf attachment file
        include_payment_link: Whether to include a payment link 

    """
    
    try:
        # Retrieve email credentials from environment variables
        sender_email = os.getenv("SENDER_EMAIL")
        sender_password = os.getenv("SENDER_APP_PASSWORD")

        if not sender_email or not sender_password:
            raise ValueError("Email credentials not found in environment variables")

        # SMTP server configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        # Compose email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        

        greeting_body = f"""Hi {tenant_first_name},\nThank you for contacting us. """
        # Prepare email body
        if include_payment_link:
            msg['Subject'] = "Rent Payment Link Details"
            email_body = greeting_body+"PLease follow below link for payment -   abc.xyz@Pqr"

            msg.attach(MIMEText(email_body, 'plain'))
        else:
            msg['Subject'] = "Lease Renewal Agreement"

            email_body = greeting_body+"Please find the lease agreement below."
            msg.attach(MIMEText(email_body, 'plain'))

            # Attach file if provided
            if attachment_path and os.path.exists(attachment_path):
                try:
                    with open(attachment_path, 'rb') as file:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(file.read())
                        encoders.encode_base64(part)
                        part.add_header(
                            'Content-Disposition', 
                            f'attachment; filename="{os.path.basename(attachment_path)}"'
                        )
                        msg.attach(part)
                except Exception as attach_error:
                    print(f"Error attaching file: {attach_error}")
                # Continue sending email even if attachment fails

        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            print(f"Email sent successfully to {recipient_email}")

        return f"Email successfully sent to {recipient_email}"

    except smtplib.SMTPException as smtp_error:
        print(f"SMTP error occurred: {smtp_error}")
        return f"Failed to send email: SMTP error - {smtp_error}"
    except Exception as error:
        print(f"Unexpected error occurred: {error}")
        return f"Failed to send email: Unexpected error - {error}"

    
agreement_and_payment_mailer_tool = StructuredTool.from_function(
    name="agreement_and_payment_mailer_tool",
    func=agreement_and_payment_mailer,
    description="Sends an email with an optional attachment and payment link to the recipient.",
    input_schema=AgreementAndRentPaymentMailerInput)

class CalculateOfferInput(BaseModel):
    max_rent: float = Field(description="The maximum rent")
    min_rent: float = Field(description="The minimum acceptable rent")
    iteration: int = Field(description="The current iteration (1 for first, 2 for second, etc.)")
    # buffer: float = Field(description="Additional buffer added to the minimum rent for the final offer", default=0)


def calculate_stepped_rent_offer(max_rent, min_rent, iteration):
    """
    Calculates the rental offer based on iterations, reducing by 2% of max_rent each time.

    Args:
    - max_rent (float): The maximum rent (starting point)
    - min_rent (float): The minimum acceptable rent
    - iteration (int): The current iteration (1 for first, 2 for second, etc.)
    - buffer (float): Additional buffer added to the minimum rent (default: 0)

    Returns:
    - float: The calculated offer for the given iteration, ensuring it doesn't fall below min_rent
    
    Example:
    >>> calculate_offer(1650, 1530, 1)  # First iteration
    1617.0
    >>> calculate_offer(1650, 1530, 3)  # Third iteration
    1551.0
    """
    # Calculate reduction amount (2% of max_rent)
    reduction_per_step = max_rent * 0.02
    
    # Calculate total reduction based on iteration
    total_reduction = reduction_per_step * iteration
    
    # Calculate proposed offer
    proposed_offer = max_rent - total_reduction
    
    # If the proposed offer would fall below minimum rent, return the last valid offer
    if proposed_offer < min_rent:
        # Calculate how many iterations we can do before hitting minimum
        max_iterations = int((max_rent - min_rent) / reduction_per_step)
        # Return the offer at the last valid iteration
        return max_rent - (reduction_per_step * max_iterations)
    
    return proposed_offer

calculate_offer_tool = StructuredTool.from_function(
    name="calculate_offer_tool",
    func = calculate_stepped_rent_offer,
    input_schema=CalculateOfferInput,
    description="Calculates the rental offer based on iterations. Useful when need to negotiate rents with tenants."
)


class FormatPhoneNumberInput(BaseModel):
    phone_number: str = Field(description="The phone number to be formatted")
#extra
# @tool(parse_docstring=False, args_schema=FormatPhoneNumberInput)
def format_phone_number(phone_number: str) -> str:
    """Format a phone number to remove non-numeric characters or spaces.

    Args:
        phone_number: The phone number as a string, which may contain non-numeric characters or spaces.
    """
    
    # Remove all non-numeric characters
    formatted_number = re.sub(r'\D', '', phone_number)
    return formatted_number

format_phone_number_tool = StructuredTool.from_function(
    name="format_phone_number_tool",
    func=format_phone_number,
    input_schema=FormatPhoneNumberInput,
    description="Format a phone number to remove non-numeric characters or spaces."
)