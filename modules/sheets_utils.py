"""
Google Sheets utility functions for logging video uploads.
"""

import os
import logging
import sys
from datetime import datetime
import gspread
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class GoogleSheetsLogger:
    """Class for logging upload information to Google Sheets"""
    
    def __init__(self, spreadsheet_id):
        """
        Initialize Google Sheets logger.
        
        Args:
            spreadsheet_id: ID of the Google Spreadsheet to use for logging
        """
        self.spreadsheet_id = spreadsheet_id
        
        try:
            # Check if running in Google Colab
            in_colab = 'google.colab' in sys.modules
            
            # Try multiple credential options in order of preference
            if os.path.exists('google_sheets_credentials.json'):
                logger.info("Using google_sheets_credentials.json for Sheets authentication")
                try:
                    credentials = service_account.Credentials.from_service_account_file(
                        'google_sheets_credentials.json',
                        scopes=['https://www.googleapis.com/auth/spreadsheets']
                    )
                    self.client = gspread.authorize(credentials)
                    self.sheet = self.client.open_by_key(spreadsheet_id).sheet1
                except Exception as e:
                    logger.warning(f"Failed to use google_sheets_credentials.json as service account: {str(e)}")
                    # Try as OAuth client credentials
                    try:
                        self.client = gspread.oauth(
                            credentials_filename='google_sheets_credentials.json',
                        )
                        self.sheet = self.client.open_by_key(spreadsheet_id).sheet1
                    except Exception as e2:
                        logger.warning(f"Failed to use google_sheets_credentials.json as OAuth client: {str(e2)}")
                        raise
            elif os.path.exists('credentials.json'):
                # Fallback to credentials.json
                logger.info("Fallback to credentials.json for Sheets authentication")
                try:
                    credentials = service_account.Credentials.from_service_account_file(
                        'credentials.json',
                        scopes=['https://www.googleapis.com/auth/spreadsheets']
                    )
                    self.client = gspread.authorize(credentials)
                    self.sheet = self.client.open_by_key(spreadsheet_id).sheet1
                except Exception as e:
                    logger.warning(f"Failed to use credentials.json: {str(e)}")
                    raise
            else:
                # Use API key (with limited functionality)
                logger.info("No credentials file found, using API key if available")
                api_key = os.getenv('GOOGLE_SHEETS_API_KEY')
                if not api_key:
                    logger.warning("Google Sheets API key not found in environment variables")
                    if in_colab:
                        logger.info("In Colab: Creating dummy sheet for testing mode")
                        self.client = None
                        self.sheet = None
                        return
                    else:
                        raise ValueError("Google Sheets API key not found in environment variables")
                        
                self.service = build('sheets', 'v4', developerKey=api_key)
                self.client = None
                self.sheet = None
                
            logger.info("Google Sheets logger initialized successfully")
            
            # Ensure the spreadsheet has the correct headers
            self._ensure_headers()
            
        except Exception as e:
            if in_colab:
                logger.error(f"Error initializing Google Sheets logger (continuing in Colab): {str(e)}")
                # In Colab and testing, we'll create a dummy logger
                self.client = None
                self.sheet = None
            else:
                logger.error(f"Error initializing Google Sheets logger: {str(e)}")
                raise
    
    def _ensure_headers(self):
        """Ensure that the spreadsheet has the correct headers"""
        if not self.sheet:
            return  # Skip for API key or dummy logger
            
        try:
            # Expected headers
            expected_headers = ['Video ID', 'Title', 'Upload Date', 'YouTube URL', 'Channel', 'Status']
            
            # Get existing headers
            existing_headers = self.sheet.row_values(1)
            
            if not existing_headers:
                # Sheet is empty, add headers
                self.sheet.append_row(expected_headers)
                logger.info("Added headers to empty spreadsheet")
            elif existing_headers != expected_headers:
                # Headers don't match, update them
                self.sheet.update('A1', [expected_headers])
                logger.info("Updated headers in spreadsheet")
        except Exception as e:
            logger.warning(f"Error ensuring headers: {str(e)}")
            
    def log_upload(self, video_id, title, youtube_url, channel, status='Uploaded'):
        """
        Log a video upload to the spreadsheet
        
        Args:
            video_id: ID of the video on Google Drive
            title: Title of the video
            youtube_url: YouTube URL of the uploaded video
            channel: Name of the YouTube channel
            status: Upload status
        """
        if not self.sheet:
            logger.info(f"Dummy log: {video_id} - {title} - {youtube_url} - {channel}")
            return True
            
        try:
            # Check if video has already been logged for this channel
            if self.is_video_uploaded(video_id, channel):
                logger.info(f"Video {video_id} already logged for channel {channel}")
                return False
            
            # Current date
            upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Append row to sheet
            self.sheet.append_row([video_id, title, upload_date, youtube_url, channel, status])
            
            logger.info(f"Logged upload of video {title} to channel {channel}")
            return True
            
        except Exception as e:
            logger.error(f"Error logging upload: {str(e)}")
            return False
    
    def is_video_uploaded(self, video_id, channel):
        """
        Check if a video has already been uploaded by checking the Google Sheet.
        
        Args:
            video_id: The Google Drive ID of the video
            channel: The YouTube channel name that the video was uploaded to
            
        Returns:
            Boolean indicating if the video has already been uploaded
        """
        try:
            # Check if we're using service account or API key
            if self.sheet:
                # Using service account
                # Find all cells with video_id
                cells = self.sheet.findall(video_id)
                
                # For each cell, get the channel name from column F
                for cell in cells:
                    if cell.col == 1:  # First column (Video ID)
                        row = cell.row
                        existing_channel = self.sheet.cell(row, 5).value  # Column F (Channel)
                        if existing_channel == channel:
                            return True
                return False
            else:
                # Using API key
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range="A2:F1000"  # Skip header row, get all data
                ).execute()
                
                values = result.get('values', [])
                for row in values:
                    if len(row) >= 1 and row[0] == video_id and len(row) >= 6 and row[5] == channel:
                        return True
                return False
                
        except Exception as e:
            logger.error(f"Error checking if video {video_id} is already uploaded: {str(e)}")
            # Default to False to avoid skipping uploads due to errors
            return False
    
    def get_uploaded_channels(self, video_id):
        """
        Get the list of channels that a video has been uploaded to.
        
        Args:
            video_id: The Google Drive ID of the video
            
        Returns:
            List of channel names that the video has been uploaded to, or empty list if none
        """
        channels = []
        try:
            # Check if we're using service account or API key
            if self.sheet:
                # Using service account
                # Find all cells with video_id
                cells = self.sheet.findall(video_id)
                
                # For each cell, get the channel name from column F
                for cell in cells:
                    if cell.col == 1:  # First column (Video ID)
                        row = cell.row
                        channel = self.sheet.cell(row, 6).value  # Column F (Channel)
                        if channel:
                            channels.append(channel)
            else:
                # Using API key
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range="A2:F1000"  # Skip header row, get all data
                ).execute()
                
                values = result.get('values', [])
                for row in values:
                    if len(row) >= 1 and row[0] == video_id:
                        if len(row) >= 6 and row[5]:  # Check Channel column
                            channels.append(row[5])
            
            return channels
                
        except Exception as e:
            logger.error(f"Error getting uploaded channels for video {video_id}: {str(e)}")
            return []
