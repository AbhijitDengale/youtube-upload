"""
Utility functions for downloading files from Google Drive links.
"""

import os
import re
import requests
import logging

logger = logging.getLogger(__name__)

def extract_file_id_from_drive_link(drive_link):
    """
    Extract the file ID from a Google Drive link.
    
    Args:
        drive_link: Google Drive sharing link
        
    Returns:
        File ID extracted from the link
    """
    # Regular expression pattern to extract the file ID
    pattern = r'/d/([a-zA-Z0-9_-]+)'
    match = re.search(pattern, drive_link)
    
    if match:
        return match.group(1)
    else:
        logger.error(f"Could not extract file ID from link: {drive_link}")
        return None

def download_file_from_drive(drive_link, output_path):
    """
    Download a file from a Google Drive link.
    
    Args:
        drive_link: Google Drive sharing link
        output_path: Path where the file should be saved
        
    Returns:
        Path to the downloaded file, or None if download failed
    """
    file_id = extract_file_id_from_drive_link(drive_link)
    if not file_id:
        return None
    
    # Make sure the directory exists
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
    
    # Google Drive direct download URL
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    
    try:
        # Create session for handling cookies
        session = requests.Session()
        
        # First request to get confirmation token for large files
        response = session.get(url, stream=True)
        
        # Check if file requires confirmation (usually for larger files)
        for key, value in response.cookies.items():
            if key.startswith('download_warning'):
                url = f"{url}&confirm={value}"
                break
        
        # Download the file
        response = session.get(url, stream=True)
        response.raise_for_status()
        
        # Save the file
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)
        
        logger.info(f"Successfully downloaded file to {output_path}")
        return output_path
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error downloading file from Google Drive: {str(e)}")
        return None

def download_credentials(drive_api_key_link, sheets_api_key_link):
    """
    Download API key files from Google Drive links.
    
    Args:
        drive_api_key_link: Google Drive link for Drive API key
        sheets_api_key_link: Google Drive link for Sheets API key
        
    Returns:
        Tuple of (drive_credentials_path, sheets_credentials_path)
    """
    # Download Drive API key
    drive_credentials_path = None
    if drive_api_key_link:
        drive_credentials_path = download_file_from_drive(
            drive_api_key_link, 
            "google_drive_credentials.json"
        )
        if drive_credentials_path:
            logger.info("Downloaded Google Drive API credentials")
        else:
            logger.error("Failed to download Google Drive API credentials")
    
    # Download Sheets API key
    sheets_credentials_path = None
    if sheets_api_key_link:
        sheets_credentials_path = download_file_from_drive(
            sheets_api_key_link, 
            "google_sheets_credentials.json"
        )
        if sheets_credentials_path:
            logger.info("Downloaded Google Sheets API credentials")
        else:
            logger.error("Failed to download Google Sheets API credentials")
    
    return (drive_credentials_path, sheets_credentials_path)
