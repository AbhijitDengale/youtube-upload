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
                        from oauth2client.service_account import ServiceAccountCredentials
                        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
                        credentials = ServiceAccountCredentials.from_json_keyfile_name('google_sheets_credentials.json', scope)
                        self.client = gspread.authorize(credentials)
                        self.sheet = self.client.open_by_key(spreadsheet_id).sheet1
                    except Exception as e2:
                        logger.warning(f"Failed to use google_sheets_credentials.json with oauth2client: {str(e2)}")
                        if in_colab:
                            logger.error(f"Error initializing Google Sheets logger (continuing in Colab): {str(e2)}")
                            # Create a dummy logger for Colab environment
                            self._create_dummy_logger()
                        else:
                            raise ValueError(f"Failed to initialize Google Sheets logger: {str(e2)}")
            elif in_colab:
                # In Colab with no credentials file, try to use Colab's authentication
                try:
                    from google.colab import auth
                    auth.authenticate_user()
                    from oauth2client.client import GoogleCredentials
                    credentials = GoogleCredentials.get_application_default()
                    self.client = gspread.authorize(credentials)
                    self.sheet = self.client.open_by_key(spreadsheet_id).sheet1
                except Exception as e:
                    logger.warning(f"Failed to authenticate with Colab: {str(e)}")
                    # Create a dummy logger
                    self._create_dummy_logger()
            else:
                raise FileNotFoundError("Google Sheets credentials not found")
                
            # Check if headers are properly set up (if not using dummy logger)
            if not hasattr(self, 'dummy_logger'):
                self._setup_headers()
                
        except Exception as e:
            logger.error(f"Error initializing Google Sheets logger: {str(e)}")
            raise
            
    def _create_dummy_logger(self):
        """Create a dummy logger that just logs but doesn't interact with Google Sheets"""
        logger.warning("Creating dummy Google Sheets logger for testing")
        self.dummy_logger = True
        self.history = []  # Store logging history in memory
        
    def _setup_headers(self):
        """Set up headers in the spreadsheet if not already present"""
        try:
            # Get all values from the first row
            first_row = self.sheet.row_values(1)
            
            # Check if we need to set up headers
            if not first_row or len(first_row) < 6:
                # Set up headers
                headers = [
                    "Video ID", 
                    "Video Name", 
                    "Upload Date", 
                    "Channel", 
                    "Folder Path",
                    "Status"
                ]
                self.sheet.update([headers])
                logger.info("Set up headers in Google Sheets")
        except Exception as e:
            logger.error(f"Error setting up headers: {str(e)}")
    
    def log_upload(self, video_id, video_name, channel, folder_path, status="Uploaded"):
        """
        Log a video upload to Google Sheets
        
        Args:
            video_id: ID of the video in Google Drive
            video_name: Name of the video
            channel: YouTube channel the video was uploaded to
            folder_path: Path to the folder in Google Drive
            status: Upload status (default: "Uploaded")
        """
        if hasattr(self, 'dummy_logger') and self.dummy_logger:
            # Just store in memory for dummy logger
            logger.info(f"Dummy log: {video_id}, {video_name}, {channel}, {folder_path}, {status}")
            self.history.append({
                "video_id": video_id,
                "video_name": video_name,
                "upload_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "channel": channel,
                "folder_path": folder_path,
                "status": status
            })
            return
            
        try:
            # Format current date
            upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Prepare row data
            row_data = [video_id, video_name, upload_date, channel, folder_path, status]
            
            # Append row
            self.sheet.append_row(row_data)
            logger.info(f"Logged upload to Google Sheets: {video_name} to {channel}")
        except Exception as e:
            logger.error(f"Error logging to Google Sheets: {str(e)}")
    
    def get_uploaded_channels(self, video_id):
        """
        Get list of channels a video has been uploaded to
        
        Args:
            video_id: ID of the video in Google Drive
            
        Returns:
            List of channel names the video has been uploaded to
        """
        if hasattr(self, 'dummy_logger') and self.dummy_logger:
            # Return from memory for dummy logger
            channels = []
            for entry in self.history:
                if entry["video_id"] == video_id and entry["status"] == "Uploaded":
                    channels.append(entry["channel"])
            return channels
            
        try:
            # Get all rows
            all_rows = self.sheet.get_all_records()
            
            # Filter by video ID and status "Uploaded"
            uploaded_entries = [row for row in all_rows if row.get("Video ID") == video_id and row.get("Status") == "Uploaded"]
            
            # Extract channel names
            channels = [entry.get("Channel") for entry in uploaded_entries]
            
            return channels
        except Exception as e:
            logger.error(f"Error getting uploaded channels: {str(e)}")
            return []
