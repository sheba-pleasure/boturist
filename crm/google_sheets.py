import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict, Optional
import logging
from datetime import datetime
from celery import shared_task

logger = logging.getLogger(__name__)

class GoogleSheetsManager:
    def __init__(self):
        """Initialize Google Sheets connection"""
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        credentials = Credentials.from_service_account_file(
            'config/google_credentials.json',
            scopes=scopes
        )
        
        self.client = gspread.authorize(credentials)
    
    def get_or_create_spreadsheet(self, title: str) -> gspread.Spreadsheet:
        """Get existing spreadsheet or create new one"""
        try:
            return self.client.open(title)
        except gspread.SpreadsheetNotFound:
            return self.client.create(title)
    
    async def setup_requests_sheet(self) -> None:
        """Setup requests tracking spreadsheet"""
        spreadsheet = self.get_or_create_spreadsheet('Заявки клиентов')
        
        # Setup main worksheet
        worksheet = spreadsheet.worksheet('Заявки')
        headers = [
            'ID заявки',
            'Дата',
            'Клиент',
            'Категория',
            'Текст заявки',
            'Статус',
            'Ответственный',
            'Комментарии'
        ]
        worksheet.update('A1:H1', [headers])
    
    async def add_request(self, request_data: Dict) -> None:
        """Add new request to spreadsheet"""
        try:
            spreadsheet = self.get_or_create_spreadsheet('Заявки клиентов')
            worksheet = spreadsheet.worksheet('Заявки')
            
            # Prepare row data
            row = [
                request_data['id'],
                datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                request_data['client_name'],
                request_data['category'],
                request_data['text'],
                'Новая',
                '',
                ''
            ]
            
            # Append row
            worksheet.append_row(row)
            
        except Exception as e:
            logger.error(f"Error adding request to Google Sheets: {e}")
    
    async def update_request_status(self, request_id: str, status: str, 
                                  assignee: Optional[str] = None,
                                  comment: Optional[str] = None) -> None:
        """Update request status in spreadsheet"""
        try:
            spreadsheet = self.get_or_create_spreadsheet('Заявки клиентов')
            worksheet = spreadsheet.worksheet('Заявки')
            
            # Find request row
            cell = worksheet.find(request_id)
            if not cell:
                logger.error(f"Request {request_id} not found in spreadsheet")
                return
            
            row = cell.row
            
            # Update status
            worksheet.update_cell(row, 6, status)
            
            # Update assignee if provided
            if assignee:
                worksheet.update_cell(row, 7, assignee)
            
            # Add comment if provided
            if comment:
                current_comments = worksheet.cell(row, 8).value
                new_comment = f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}: {comment}"
                if current_comments:
                    new_comment = f"{current_comments}\n{new_comment}"
                worksheet.update_cell(row, 8, new_comment)
            
        except Exception as e:
            logger.error(f"Error updating request in Google Sheets: {e}")

@shared_task
async def sync_requests_to_sheets() -> None:
    """Sync all new requests to Google Sheets"""
    from pymongo import MongoClient
    from django.conf import settings
    
    try:
        # Connect to MongoDB
        client = MongoClient(settings.MONGODB_URI)
        db = client.bot_data
        
        # Get new requests
        new_requests = db.requests.find({'synced_to_sheets': {'$ne': True}})
        
        sheets_manager = GoogleSheetsManager()
        
        for request in new_requests:
            # Get user info
            user = db.users.find_one({'user_id': request['user_id']})
            
            # Prepare request data
            request_data = {
                'id': str(request['_id']),
                'client_name': f"{user['first_name']} {user.get('last_name', '')}",
                'category': request['category'],
                'text': request['text']
            }
            
            # Add to sheets
            await sheets_manager.add_request(request_data)
            
            # Mark as synced
            db.requests.update_one(
                {'_id': request['_id']},
                {'$set': {'synced_to_sheets': True}}
            )
            
    except Exception as e:
        logger.error(f"Error syncing requests to Google Sheets: {e}")

@shared_task
async def setup_sheets() -> None:
    """Initial setup of Google Sheets structure"""
    try:
        sheets_manager = GoogleSheetsManager()
        await sheets_manager.setup_requests_sheet()
    except Exception as e:
        logger.error(f"Error setting up Google Sheets: {e}") 