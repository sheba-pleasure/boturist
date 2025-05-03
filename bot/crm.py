from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials
from google.oauth2 import service_account

from config import Config

logger = logging.getLogger(__name__)

class CRMIntegration:
    """Base class for CRM integrations"""
    
    def __init__(self):
        """Initialize CRM integration"""
        pass
    
    async def create_lead(self, data: Dict[str, Any]) -> bool:
        """Create a new lead in CRM"""
        raise NotImplementedError
    
    async def update_lead(self, lead_id: str, data: Dict[str, Any]) -> bool:
        """Update lead in CRM"""
        raise NotImplementedError
    
    async def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Get lead from CRM"""
        raise NotImplementedError

class GoogleSheetsCRM(CRMIntegration):
    """Google Sheets CRM integration"""
    
    def __init__(self):
        """Initialize Google Sheets CRM"""
        super().__init__()
        
        # Set up Google Sheets credentials
        self.scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        self.creds = Credentials.from_service_account_file(
            'config/google_credentials.json',
            scopes=self.scope
        )
        
        self.client = gspread.authorize(self.creds)
        self.sheet = self.client.open_by_key(Config.GOOGLE_SHEETS_ID)
        
        # Initialize worksheets
        self.leads_sheet = self.sheet.worksheet('Leads')
        self.contacts_sheet = self.sheet.worksheet('Contacts')
    
    async def create_lead(self, data: Dict[str, Any]) -> bool:
        """Create a new lead in Google Sheets"""
        try:
            # Prepare row data
            row = [
                datetime.utcnow().isoformat(),  # Timestamp
                data.get('name', ''),           # Name
                data.get('phone', ''),          # Phone
                data.get('email', ''),          # Email
                data.get('source', ''),         # Source
                data.get('status', 'New'),      # Status
                data.get('message', ''),        # Message
                data.get('category', ''),       # Category
            ]
            
            # Append row to sheet
            self.leads_sheet.append_row(row)
            return True
            
        except Exception as e:
            logger.error(f"Error creating lead in Google Sheets: {e}")
            return False
    
    async def update_lead(self, lead_id: str, data: Dict[str, Any]) -> bool:
        """Update lead in Google Sheets"""
        try:
            # Find row by lead ID
            cell = self.leads_sheet.find(lead_id)
            if not cell:
                return False
            
            row = cell.row
            
            # Update specific columns based on data
            updates = []
            if 'status' in data:
                status_col = 6  # Status column
                updates.append((row, status_col, data['status']))
            
            if 'category' in data:
                category_col = 8  # Category column
                updates.append((row, category_col, data['category']))
            
            # Batch update
            if updates:
                cells = [self.leads_sheet.cell(row, col, value) for row, col, value in updates]
                self.leads_sheet.update_cells(cells)
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating lead in Google Sheets: {e}")
            return False
    
    async def get_lead(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Get lead from Google Sheets"""
        try:
            # Find row by lead ID
            cell = self.leads_sheet.find(lead_id)
            if not cell:
                return None
            
            row = self.leads_sheet.row_values(cell.row)
            
            # Map row to dictionary
            return {
                'timestamp': row[0],
                'name': row[1],
                'phone': row[2],
                'email': row[3],
                'source': row[4],
                'status': row[5],
                'message': row[6],
                'category': row[7]
            }
            
        except Exception as e:
            logger.error(f"Error getting lead from Google Sheets: {e}")
            return None
    
    async def get_all_leads(self) -> List[Dict[str, Any]]:
        """Get all leads from Google Sheets"""
        try:
            # Get all rows except header
            rows = self.leads_sheet.get_all_values()[1:]
            
            # Map rows to dictionaries
            leads = []
            for row in rows:
                leads.append({
                    'timestamp': row[0],
                    'name': row[1],
                    'phone': row[2],
                    'email': row[3],
                    'source': row[4],
                    'status': row[5],
                    'message': row[6],
                    'category': row[7]
                })
            
            return leads
            
        except Exception as e:
            logger.error(f"Error getting all leads from Google Sheets: {e}")
            return []
    
    async def add_contact(self, data: Dict[str, Any]) -> bool:
        """Add contact to Google Sheets"""
        try:
            # Prepare row data
            row = [
                datetime.utcnow().isoformat(),  # Timestamp
                data.get('name', ''),           # Name
                data.get('phone', ''),          # Phone
                data.get('email', ''),          # Email
                data.get('telegram_id', ''),    # Telegram ID
                data.get('source', ''),         # Source
                data.get('notes', ''),          # Notes
            ]
            
            # Append row to contacts sheet
            self.contacts_sheet.append_row(row)
            return True
            
        except Exception as e:
            logger.error(f"Error adding contact to Google Sheets: {e}")
            return False
    
    async def search_contacts(self, query: str) -> List[Dict[str, Any]]:
        """Search contacts in Google Sheets"""
        try:
            # Get all contacts
            rows = self.contacts_sheet.get_all_values()[1:]  # Skip header
            
            # Filter contacts based on query
            matching_contacts = []
            for row in rows:
                if any(query.lower() in field.lower() for field in row):
                    matching_contacts.append({
                        'timestamp': row[0],
                        'name': row[1],
                        'phone': row[2],
                        'email': row[3],
                        'telegram_id': row[4],
                        'source': row[5],
                        'notes': row[6]
                    })
            
            return matching_contacts
            
        except Exception as e:
            logger.error(f"Error searching contacts in Google Sheets: {e}")
            return []

class CRMHub:
    """Hub for managing multiple CRM integrations"""
    
    def __init__(self):
        """Initialize CRM hub"""
        self.crm_systems = {
            'google_sheets': GoogleSheetsCRM()
        }
        
        # Default CRM system
        self.default_crm = 'google_sheets'
    
    async def create_lead(self, data: Dict[str, Any], crm_system: Optional[str] = None) -> bool:
        """Create lead in specified CRM system"""
        system = crm_system or self.default_crm
        if system in self.crm_systems:
            return await self.crm_systems[system].create_lead(data)
        return False
    
    async def update_lead(self, lead_id: str, data: Dict[str, Any], crm_system: Optional[str] = None) -> bool:
        """Update lead in specified CRM system"""
        system = crm_system or self.default_crm
        if system in self.crm_systems:
            return await self.crm_systems[system].update_lead(lead_id, data)
        return False
    
    async def get_lead(self, lead_id: str, crm_system: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get lead from specified CRM system"""
        system = crm_system or self.default_crm
        if system in self.crm_systems:
            return await self.crm_systems[system].get_lead(lead_id)
        return None
    
    async def add_contact(self, data: Dict[str, Any], crm_system: Optional[str] = None) -> bool:
        """Add contact to specified CRM system"""
        system = crm_system or self.default_crm
        if system in self.crm_systems:
            return await self.crm_systems[system].add_contact(data)
        return False
    
    async def search_contacts(self, query: str, crm_system: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search contacts in specified CRM system"""
        system = crm_system or self.default_crm
        if system in self.crm_systems:
            return await self.crm_systems[system].search_contacts(query)
        return [] 