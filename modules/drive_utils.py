"""
Google Drive API utility functions for the YouTube upload automation system.
"""

import os
import io
import logging
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

class GoogleDriveClient:
    """Client for interacting with Google Drive API"""
    
    def __init__(self):
        """Initialize the Google Drive API client"""
        try:
            # Check if we're using API key or OAuth credentials
            if os.path.exists('credentials.json'):
                creds = service_account.Credentials.from_service_account_file(
                    'credentials.json',
                    scopes=['https://www.googleapis.com/auth/drive.readonly']
                )
            else:
                # Using API key
                api_key = os.getenv('GOOGLE_DRIVE_API_KEY')
                if not api_key:
                    raise ValueError("Google Drive API key not found in environment variables")
                self.drive_service = build('drive', 'v3', developerKey=api_key)
                return
                
            self.drive_service = build('drive', 'v3', credentials=creds)
            logger.info("Google Drive API client initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing Google Drive client: {str(e)}")
            raise
    
    def get_folders(self, parent_id='root'):
        """Get all folders in the specified parent folder"""
        try:
            query = f"mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            folders = results.get('files', [])
            return folders
        except Exception as e:
            logger.error(f"Error getting folders: {str(e)}")
            return []
    
    def get_subfolders(self, folder_id):
        """Get all subfolders within a specified folder"""
        return self.get_folders(parent_id=folder_id)
    
    def get_videos(self, folder_id):
        """Get all video files within a folder"""
        try:
            # Query for video files
            query = f"mimeType contains 'video/' and '{folder_id}' in parents and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, mimeType, size)"
            ).execute()
            
            videos = results.get('files', [])
            return videos
        except Exception as e:
            logger.error(f"Error getting videos: {str(e)}")
            return []
    
    def find_file_by_name(self, folder_id, filename):
        """Find a specific file by name within a folder"""
        try:
            query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, mimeType)"
            ).execute()
            
            files = results.get('files', [])
            return files[0] if files else None
        except Exception as e:
            logger.error(f"Error finding file {filename}: {str(e)}")
            return None
    
    def download_video(self, file_id, filename):
        """Download a video file from Google Drive"""
        try:
            request = self.drive_service.files().get_media(fileId=file_id)
            
            # Create a temporary file to save the video
            output_path = os.path.join("temp", filename)
            os.makedirs("temp", exist_ok=True)
            
            with open(output_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    logger.info(f"Download {int(status.progress() * 100)}%")
            
            return output_path
        except Exception as e:
            logger.error(f"Error downloading video {filename}: {str(e)}")
            return None
    
    def download_file(self, file_info, filename):
        """Download any file from Google Drive given its file info"""
        try:
            file_id = file_info.get('id')
            request = self.drive_service.files().get_media(fileId=file_id)
            
            # Create a temporary file
            output_path = os.path.join("temp", filename)
            os.makedirs("temp", exist_ok=True)
            
            with open(output_path, 'wb') as f:
                downloader = MediaIoBaseDownload(f, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            return output_path
        except Exception as e:
            logger.error(f"Error downloading file {filename}: {str(e)}")
            return None
    
    def read_text_file(self, file_info):
        """Read and return the contents of a text file from Google Drive"""
        try:
            if not file_info:
                return None
                
            file_id = file_info.get('id')
            request = self.drive_service.files().get_media(fileId=file_id)
            
            file_content = io.BytesIO()
            downloader = MediaIoBaseDownload(file_content, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            
            file_content.seek(0)
            return file_content.read().decode('utf-8').strip()
        except Exception as e:
            logger.error(f"Error reading text file: {str(e)}")
            return None
