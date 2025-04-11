"""
Google Sheets utility functions for logging video uploads.
"""

import os
import logging
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
            # Check if we have service account credentials
            if os.path.exists('credentials.json'):
                credentials = service_account.Credentials.from_service_account_file(
                    'credentials.json',
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                self.client = gspread.authorize(credentials)
                self.sheet = self.client.open_by_key(spreadsheet_id).sheet1
            else:
                # Use API key (with limited functionality)
                api_key = os.getenv('GOOGLE_SHEETS_API_KEY')
                if not api_key:
                    raise ValueError("Google Sheets API key not found in environment variables")
                self.service = build('sheets', 'v4', developerKey=api_key)
                self.client = None
                self.sheet = None
                
            logger.info("Google Sheets logger initialized successfully")
            
            # Ensure the spreadsheet has the correct headers
            self._ensure_headers()
            
        except Exception as e:
            logger.error(f"Error initializing Google Sheets logger: {str(e)}")
            raise
    
    def _ensure_headers(self):
        """Ensure the spreadsheet has the correct headers"""
        try:
            # Check if we're using service account or API key
            if self.sheet:
                # Using service account
                headers = self.sheet.row_values(1)
                if not headers:
                    # Spreadsheet is empty, add headers
                    headers = ["Video ID", "Video Name", "Folder Path", "YouTube URL", "Upload Time", "Channel"]
                    self.sheet.update('A1:F1', [headers])
                    logger.info("Added headers to Google Sheet")
                elif len(headers) < 6 or headers[5] != "Channel":
                    # Add channel column if it doesn't exist
                    headers.append("Channel")
                    self.sheet.update('A1:F1', [headers])
                    logger.info("Added Channel column to Google Sheet")
            else:
                # Using API key - can only read, not write
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range="A1:F1"
                ).execute()
                
                values = result.get('values', [])
                if not values:
                    logger.warning("Cannot add headers to Google Sheet with API key. Please add headers manually.")
                elif len(values[0]) < 6:
                    logger.warning("Missing 'Channel' column. Please add it manually.")
                
        except Exception as e:
            logger.error(f"Error ensuring headers in Google Sheet: {str(e)}")
    
    def is_video_uploaded(self, video_id):
        """
        Check if a video has already been uploaded by checking the Google Sheet.
        
        Args:
            video_id: The Google Drive ID of the video
            
        Returns:
            Boolean indicating if the video has already been uploaded
        """
        try:
            # Check if we're using service account or API key
            if self.sheet:
                # Using service account
                # Find the video ID in the first column
                cell = self.sheet.find(video_id)
                return cell is not None
            else:
                # Using API key
                result = self.service.spreadsheets().values().get(
                    spreadsheetId=self.spreadsheet_id,
                    range="A:A"
                ).execute()
                
                values = result.get('values', [])
                for row in values:
                    if row and row[0] == video_id:
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
    
    def log_upload(self, video_id, video_name, folder_path, youtube_url, upload_time=None, channel="default"):
        """
        Log a successful video upload to Google Sheets.
        
        Args:
            video_id: The Google Drive ID of the video
            video_name: The name of the video file
            folder_path: The path to the folder containing the video
            youtube_url: The URL of the uploaded YouTube video
            upload_time: Time of upload (default: current time)
            channel: The YouTube channel name that the video was uploaded to
            
        Returns:
            Boolean indicating success or failure
        """
        try:
            if not upload_time:
                upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
            # Row to add to the sheet
            row = [video_id, video_name, folder_path, youtube_url, upload_time, channel]
            
            # Check if we're using service account or API key
            if self.sheet:
                # Using service account, append the row
                self.sheet.append_row(row)
                logger.info(f"Logged upload of {video_name} to channel {channel} in Google Sheet")
                return True
            else:
                # Using API key (limited, can only read)
                logger.error("Cannot log upload with API key. Service account credentials required.")
                return False
                
        except Exception as e:
            logger.error(f"Error logging upload to Google Sheet: {str(e)}")
            return False
