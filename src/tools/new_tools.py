from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import sqlite3
from datetime import datetime
import logging as lg
from langchain_core.tools import StructuredTool
from src.constants.sql_tables import RENT_TABLE_NAME, LEASE_TABLE_NAME


# Database connection function
def get_db_connection():
    """Create and return a database connection"""
    return sqlite3.connect('lease_real_estate.db')

# Input schemas
class TenantVerificationInput(BaseModel):
    tenant_name: str = Field(description="Name of the tenant to verify")

class ApartmentVerificationInput(BaseModel):
    tenant_name: str = Field(description="Name of the tenant")
    apartment_number: str = Field(description="Apartment number to verify")

class PhoneVerificationInput(BaseModel):
    tenant_name: str = Field(description="Name of the tenant")
    phone_number: str = Field(description="Phone number to verify")

class GetLeaseDetailsInput(BaseModel):
    tenant_name: str = Field(description="Name of the tenant")
    apartment_number: str = Field(description="Apartment number")

# Authentication Flow Tools
def verify_tenant(tenant_name: str) -> Dict[str, Any]:
    """Verify if tenant exists in the database with the given name"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = f"""
            SELECT Tenant_ID, Tenant_Name 
            FROM {LEASE_TABLE_NAME} 
            WHERE Tenant_Name = ? COLLATE NOCASE
            """
            cursor.execute(query, (tenant_name,))
            result = cursor.fetchone()
            
            if result:
                return {
                    "exists": True,
                    "tenant_id": result[0],
                    "tenant_name": result[1]
                }
            return {
                "exists": False,
                "message": "Tenant not found in our records"
            }
    except Exception as e:
        lg.error(f"Error in verify_tenant_tool: {e}")
        return {"error": str(e)}

verify_tenant_tool = StructuredTool.from_function(
    name="verify_tenant_tool",
    func=verify_tenant,
    input_schema=TenantVerificationInput,
    description="Verify if tenant exists in the database with the given name."
)

def verify_tenant_apartment(tenant_name: str, apartment_number: str) -> Dict[str, Any]:
    """Verify if apartment number matches tenant records"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = f"""
            SELECT Tenant_ID, Apartment_Number 
            FROM {LEASE_TABLE_NAME} 
            WHERE Tenant_Name = ? COLLATE NOCASE 
            AND Apartment_Number = ? COLLATE NOCASE
            """
            cursor.execute(query, (tenant_name, apartment_number))
            result = cursor.fetchone()
            
            if result:
                return {
                    "matches": True,
                    "tenant_id": result[0],
                    "apartment_number": result[1]
                }
            return {
                "matches": False,
                "message": "No matching tenant-apartment combination found"
            }
    except Exception as e:
        lg.error(f"Error in verify_tenant_apartment_tool: {e}")
        return {"error": str(e)}

verify_tenant_apartment_tool = StructuredTool.from_function(
    name="verify_tenant_apartment_tool",
    func=verify_tenant_apartment,
    input_schema=ApartmentVerificationInput,
    description="Verify if apartment number matches tenant records."
)

def verify_phone(tenant_name: str, phone_number: str) -> Dict[str, Any]:
    """Verify if phone number matches tenant records"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = f"""
            SELECT Tenant_ID, Tenant_Phone 
            FROM {LEASE_TABLE_NAME} 
            WHERE Tenant_Name = ? COLLATE NOCASE 
            AND Tenant_Phone = ?
            """
            cursor.execute(query, (tenant_name, phone_number))
            result = cursor.fetchone()
            
            if result:
                return {
                    "matches": True,
                    "tenant_id": result[0]
                }
            return {
                "matches": False,
                "message": "Phone number does not match our records"
            }
    except Exception as e:
        lg.error(f"Error in verify_phone_tool: {e}")
        return {"error": str(e)}

verify_phone_tool = StructuredTool.from_function(
    name="verify_phone_tool",
    func=verify_phone,
    input_schema=PhoneVerificationInput,
    description="Verify if phone number matches tenant records."
)

def get_tenant_email(tenant_name: str, apartment_number: str) -> Dict[str, Any]:
    """Fetch tenant's email from database"""
    try:
        global tenant_email
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = f"""
            SELECT Tenant_Email 
            FROM {LEASE_TABLE_NAME} 
            WHERE Tenant_Name = ? COLLATE NOCASE 
            AND Apartment_Number = ? COLLATE NOCASE
            """
            cursor.execute(query, (tenant_name, apartment_number))
            result = cursor.fetchone()
            
            if result:
                tenant_email = result[0]
                return tenant_email

                # return {
                #     "found": True,
                #     "tenant_email": result[0]
                # }
            return {
                "found": False,
                "message": "Email not found"
            }
    except Exception as e:
        lg.error(f"Error in get_tenant_email_tool: {e}")
        return {"error": str(e)}

get_tenant_email_tool = StructuredTool.from_function(
    name="get_tenant_email_tool",
    func=get_tenant_email,
    input_schema=GetLeaseDetailsInput,
    description="Fetch tenant's email from database. Use this tool to fetch tenant's email address always."
)

def get_lease_details(tenant_name: str, apartment_number: str) -> Dict[str, Any]:
    """Fetch complete lease details including renewal rates"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = f"""
            SELECT 
                Tenant_Email,
                Tenant_Phone,
                Lease_Start_Date,
                Lease_End_Date,
                Current_Rent,
                Min_Lease_Amount,
                Max_Lease_Amount,
                Lease_Status,
                Building,
                City,
                Owner_Name,
                Owner_Email,
                Owner_Contact_Number,
                Lease_Terms,
                Renewal_Terms
            FROM {LEASE_TABLE_NAME} 
            WHERE Tenant_Name = ? COLLATE NOCASE 
            AND Apartment_Number = ? COLLATE NOCASE
            """
            cursor.execute(query, (tenant_name, apartment_number))
            result = cursor.fetchone()
            
            if result:
                return {
                    "found": True,
                    "details": {
                        "tenant_email": result[0],
                        "tenant_phone": result[1],
                        "lease_start": result[2],
                        "lease_end": result[3],
                        "current_rent": result[4],
                        "min_rent": result[5],
                        "max_rent": result[6],
                        "status": result[7],
                        "building": result[8],
                        "city": result[9],
                        "owner_name": result[10],
                        "owner_email": result[11],
                        "owner_contact": result[12],
                        "increase_percentage": result[13]
                    }
                }
            return {
                "found": False,
                "message": "Lease details not found"
            }
    except Exception as e:
        lg.error(f"Error in get_lease_details_tool: {e}")
        return {"error": str(e)}

get_lease_details_tool = StructuredTool.from_function(
    name="get_lease_details_tool",
    func=get_lease_details,
    input_schema=GetLeaseDetailsInput,
    description="Fetch complete lease details including renewal rates."
)

def get_tenant_rent_status(tenant_name: str, apartment_number: str) -> Optional[Dict]:
    """
    Fetch current rent status for a tenant based on name and apartment number.
    
    Args:
        tenant_name (str): Name of the tenant
        apartment_number (str): Apartment number
    
    Returns:
        Optional[Dict]: Dictionary containing tenant details and rent status if found,
                       None if tenant not found
    """
    try:
        # Establish database connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
        
            # SQL query to join lease_details and rent_status tables
            query = f"""
            SELECT 
                l.Tenant_Name,
                l.Apartment_Number,
                l.Current_Rent,
                l.Lease_Status,
                l.Lease_End_Date,
                r.Status as Rent_Status
            FROM {LEASE_TABLE_NAME} l
            LEFT JOIN {RENT_TABLE_NAME} r ON l.Tenant_ID = r.Tenant_ID
            WHERE LOWER(l.Tenant_Name) = LOWER(?) 
            AND l.Apartment_Number = ?
            """
            
            # Execute query with parameters
            cursor.execute(query, (tenant_name, apartment_number))
            result = cursor.fetchone()
            
            if result:
                return {
                    'tenant_name': result[0],
                    'apartment_number': result[1],
                    'current_rent': result[2],
                    'lease_status': result[3],
                    'lease_end_date': result[4],
                    'rent_status': result[5]
                }
            return {
                "found": False,
                "message": "Tenant details not found"
            }
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        raise
        
    finally:
        if conn:
            conn.close()

check_rent_status_tool = StructuredTool.from_function(
    name="get_tenant_rent_status_tool",
    func=get_tenant_rent_status,
    input_schema=GetLeaseDetailsInput,
    description="Check current rent payment status."
)