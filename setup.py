#!/usr/bin/env python3
"""
Setup script for YouTube Upload Automation

This script helps with the initial setup:
1. Checks for dependencies
2. Guides through creating OAuth credentials (if needed)
3. Tests connectivity to all required services
4. Downloads API key files from Google Drive links
"""

import os
import sys
import json
import logging
from dotenv import load_dotenv

# Add import for the download_utils module
from modules.download_utils import download_credentials

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Google Drive links for API key files
DRIVE_API_KEY_LINK = "https://drive.google.com/file/d/152LtocR_Lvll37IW3GXJWAowLS02YBF2/view?usp=sharing"
SHEETS_API_KEY_LINK = "https://drive.google.com/file/d/1W365AG3tpzytNRnZ9darqLDLx94XYsNo/view?usp=sharing"

def check_dependencies():
    """Check if all required dependencies are installed"""
    try:
        import google
        import googleapiclient
        import google_auth_oauthlib
        import google_auth_httplib2
        import requests
        import gspread
        logger.info("✅ All required dependencies are installed")
        return True
    except ImportError as e:
        logger.error(f"❌ Missing dependency: {str(e)}")
        logger.info("Please run: pip install -r requirements.txt")
        return False

def check_env_file():
    """Check if .env file exists and has required values"""
    if not os.path.exists('.env'):
        logger.warning("❌ .env file not found")
        logger.info("Creating .env file from template...")
        if os.path.exists('.env.template'):
            with open('.env.template', 'r') as template:
                with open('.env', 'w') as env_file:
                    env_file.write(template.read())
            logger.info("✅ Created .env file. Please edit it with your API keys.")
        else:
            logger.error("❌ .env.template file not found")
        return False
    
    # Load environment variables
    load_dotenv()
    
    # Check required variables
    required_vars = [
        'GOOGLE_DRIVE_API_KEY',
        'YOUTUBE_API_KEY',
        'GOOGLE_SHEETS_API_KEY',
        'SPREADSHEET_ID',
        'TELEGRAM_BOT_TOKEN',
        'TELEGRAM_CHAT_ID'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var) or os.getenv(var).startswith('your_'):
            missing_vars.append(var)
    
    if missing_vars:
        logger.warning(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        logger.info("Please edit the .env file to add your API keys.")
        return False
    
    logger.info("✅ .env file exists and has all required variables")
    return True

def download_api_key_files():
    """Download API key files from Google Drive links"""
    logger.info("Downloading API key files from Google Drive...")
    
    drive_creds_path, sheets_creds_path = download_credentials(
        DRIVE_API_KEY_LINK, 
        SHEETS_API_KEY_LINK
    )
    
    success = True
    if not drive_creds_path:
        logger.error("❌ Failed to download Google Drive API key file")
        success = False
    else:
        # Create a symlink or copy file to credentials.json for Drive
        try:
            if os.path.exists('credentials.json'):
                os.remove('credentials.json')
            os.rename(drive_creds_path, 'credentials.json')
            logger.info("✅ Successfully set up Google Drive credentials")
        except Exception as e:
            logger.error(f"❌ Error setting up Google Drive credentials: {str(e)}")
            success = False
    
    if not sheets_creds_path:
        logger.error("❌ Failed to download Google Sheets API key file")
        success = False
    
    return success

def check_credentials_file():
    """Check if credentials.json file exists for service account auth"""
    # First try to download credentials file if it doesn't exist
    if not os.path.exists('credentials.json'):
        logger.info("credentials.json file not found. Attempting to download...")
        download_api_key_files()
    
    if not os.path.exists('credentials.json'):
        logger.warning("❌ credentials.json file not found for service account authentication")
        logger.info("Using API keys instead. Service account is recommended for full functionality.")
        return False
    
    # Validate JSON format
    try:
        with open('credentials.json', 'r') as f:
            json.load(f)
        logger.info("✅ credentials.json file exists and is valid JSON")
        return True
    except json.JSONDecodeError:
        logger.error("❌ credentials.json file exists but is not valid JSON")
        return False

def check_client_secrets_file():
    """Check if client_secret.json file exists for OAuth2 authentication"""
    if not os.path.exists('client_secret.json'):
        logger.warning("❌ client_secret.json file not found for OAuth2 authentication")
        logger.info("Using API keys instead. OAuth2 is required for YouTube uploads.")
        return False
    
    # Validate JSON format
    try:
        with open('client_secret.json', 'r') as f:
            json.load(f)
        logger.info("✅ client_secret.json file exists and is valid JSON")
        return True
    except json.JSONDecodeError:
        logger.error("❌ client_secret.json file exists but is not valid JSON")
        return False

def test_telegram_connection():
    """Test connection to Telegram bot"""
    from modules.telegram_utils import TelegramNotifier
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token or not chat_id:
        logger.warning("❌ Cannot test Telegram connection: missing bot token or chat ID")
        return False
    
    try:
        notifier = TelegramNotifier(bot_token, chat_id)
        if notifier.test_connection():
            logger.info("✅ Successfully connected to Telegram bot")
            return True
        else:
            logger.error("❌ Failed to connect to Telegram bot")
            return False
    except Exception as e:
        logger.error(f"❌ Error testing Telegram connection: {str(e)}")
        return False

def main():
    """Main setup function"""
    logger.info("Starting setup for YouTube Upload Automation")
    
    # Check dependencies
    deps_ok = check_dependencies()
    
    # Download API key files
    download_api_key_files()
    
    # Check environment variables
    env_ok = check_env_file()
    
    # Check credentials files
    creds_ok = check_credentials_file()
    client_secrets_ok = check_client_secrets_file()
    
    # Test Telegram connection if environment variables are set
    if env_ok:
        telegram_ok = test_telegram_connection()
    else:
        telegram_ok = False
    
    # Print setup summary
    logger.info("\n=== Setup Summary ===")
    logger.info(f"Dependencies: {'✅' if deps_ok else '❌'}")
    logger.info(f"Environment Variables: {'✅' if env_ok else '❌'}")
    logger.info(f"Service Account Credentials: {'✅' if creds_ok else '❌ (optional)'}")
    logger.info(f"OAuth2 Client Secrets: {'✅' if client_secrets_ok else '❌ (needed for YouTube)'}")
    logger.info(f"Telegram Connection: {'✅' if telegram_ok else '❌'}")
    
    # Determine if setup is ready
    if deps_ok and env_ok and (creds_ok or client_secrets_ok):
        logger.info("\n✅ Setup is complete! You can now run 'python main.py' to start the automation.")
    else:
        logger.warning("\n❌ Setup is incomplete. Please address the issues above before running the main script.")
        if not client_secrets_ok:
            logger.info("\nTo create OAuth2 credentials for YouTube:")
            logger.info("1. Go to https://console.cloud.google.com/")
            logger.info("2. Create a new project or select an existing one")
            logger.info("3. Enable the YouTube Data API v3")
            logger.info("4. Create OAuth2 credentials (Application type: Desktop app)")
            logger.info("5. Download the credentials as client_secret.json and place it in this directory")

if __name__ == "__main__":
    main()
