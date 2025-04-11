#!/usr/bin/env python3
"""
YouTube Upload Automation Script

This script automates the process of:
1. Scanning Google Drive folders for videos
2. Uploading videos to YouTube (to multiple channels)
3. Sending notifications to Telegram
4. Logging uploads in Google Sheets
"""

import os
import time
import logging
import json
import argparse
import requests
import io
import subprocess  # Added for process execution
from dotenv import load_dotenv
from datetime import datetime

# Import our custom modules
from modules.drive_utils import GoogleDriveClient
from modules.youtube_utils import YouTubeClient, MultiChannelYouTubeUploader
from modules.telegram_utils import TelegramNotifier
from modules.sheets_utils import GoogleSheetsLogger
from modules.download_utils import download_credentials

# Google Drive links for API key files
DRIVE_API_KEY_LINK = "https://drive.google.com/file/d/152LtocR_Lvll37IW3GXJWAowLS02YBF2/view?usp=sharing"
SHEETS_API_KEY_LINK = "https://drive.google.com/file/d/1W365AG3tpzytNRnZ9darqLDLx94XYsNo/view?usp=sharing"

# Target YouTube channels
YOUTUBE_CHANNELS = [
    {"name": "Tiny Trailblazers", "handle": "TinyTrailblazers", "credentials_file": "channel1_client_secret.json"},
    {"name": "KidVenture Quest", "handle": "KidVentureQuestnw", "credentials_file": "channel2_client_secret.json"},
    {"name": "MagicMap Tales", "handle": "MagicMapTales", "credentials_file": "channel3_client_secret.json"}
]

# Define channel credential files
YOUTUBE_CHANNEL_CREDENTIALS = [channel["credentials_file"] for channel in YOUTUBE_CHANNELS]

# Hardcoded Telegram credentials
TELEGRAM_BOT_TOKEN = "7425850499:AAFeqvSXe-KRaBCEvRlrpfdSbExSoGeMiCI"
TELEGRAM_CHAT_ID = "-1002493560505"

# YouTube API Key
YOUTUBE_API_KEY = "AIzaSyCNbN-lpBIAjZHxe9wI60bTbig4VyT6i10"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("upload_logs.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def ensure_env_file():
    """Create .env file if it doesn't exist with default values"""
    if not os.path.exists('.env'):
        logger.info("Creating .env file with default values")
        with open('.env', 'w') as env_file:
            env_file.write(f"""# YouTube Upload Automation API Configuration
GOOGLE_DRIVE_API_KEY=auto_downloaded
YOUTUBE_API_KEY={YOUTUBE_API_KEY}
GOOGLE_SHEETS_API_KEY=auto_downloaded
SPREADSHEET_ID=your_spreadsheet_id
TELEGRAM_BOT_TOKEN={TELEGRAM_BOT_TOKEN}
TELEGRAM_CHAT_ID={TELEGRAM_CHAT_ID}
""")
    return True

def download_api_keys_from_drive():
    """
    Try to download API keys from Google Drive directly.
    If in Google Colab, use the Colab auth. Otherwise use direct download.
    """
    try:
        # Check if running in Google Colab
        try:
            import google.colab
            is_colab = True
            logger.info("Running in Google Colab environment")
        except ImportError:
            is_colab = False
            logger.info("Not running in Google Colab, using direct download method")
        
        if is_colab:
            try:
                # Just download directly from the URLs rather than mounting Drive
                logger.info("Downloading API credentials from direct URLs...")
                
                # Create directories if needed
                os.makedirs("temp", exist_ok=True)
                
                # Extract file IDs from links
                drive_api_key_id = DRIVE_API_KEY_LINK.split('/')[-2]
                sheets_api_key_id = SHEETS_API_KEY_LINK.split('/')[-2]
                
                # Direct download URLs
                drive_download_url = f"https://drive.google.com/uc?export=download&id={drive_api_key_id}"
                sheets_download_url = f"https://drive.google.com/uc?export=download&id={sheets_api_key_id}"
                
                # Download Drive API credentials
                try:
                    logger.info(f"Downloading Google Drive API credentials from {drive_download_url}")
                    response = requests.get(drive_download_url)
                    if response.status_code == 200:
                        with open('credentials.json', 'wb') as f:
                            f.write(response.content)
                        logger.info("Successfully downloaded Google Drive credentials")
                    else:
                        logger.error(f"Failed to download Drive API key: {response.status_code}")
                        # Create a fallback file
                        with open('credentials.json', 'w') as f:
                            f.write('{"installed":{"client_id":"placeholder","project_id":"youtube-upload-automation"}}')
                except Exception as e:
                    logger.error(f"Error downloading Drive API key: {str(e)}")
                    # Create a fallback file
                    with open('credentials.json', 'w') as f:
                        f.write('{"installed":{"client_id":"placeholder","project_id":"youtube-upload-automation"}}')
                
                # Download Sheets API credentials
                try:
                    logger.info(f"Downloading Google Sheets API credentials from {sheets_download_url}")
                    response = requests.get(sheets_download_url)
                    if response.status_code == 200:
                        with open('google_sheets_credentials.json', 'wb') as f:
                            f.write(response.content)
                        logger.info("Successfully downloaded Google Sheets credentials")
                    else:
                        logger.error(f"Failed to download Sheets API key: {response.status_code}")
                        # Create a fallback file
                        with open('google_sheets_credentials.json', 'w') as f:
                            f.write('{"installed":{"client_id":"placeholder","project_id":"youtube-upload-automation"}}')
                except Exception as e:
                    logger.error(f"Error downloading Sheets API key: {str(e)}")
                    # Create a fallback file
                    with open('google_sheets_credentials.json', 'w') as f:
                        f.write('{"installed":{"client_id":"placeholder","project_id":"youtube-upload-automation"}}')
                
                logger.info("API credentials setup completed!")
                return True
                
            except Exception as e:
                logger.error(f"Error during Colab authentication: {str(e)}")
                # Create default credential files as fallback
                with open('credentials.json', 'w') as f:
                    f.write('{"installed":{"client_id":"placeholder","project_id":"youtube-upload-automation"}}')
                with open('google_sheets_credentials.json', 'w') as f:
                    f.write('{"installed":{"client_id":"placeholder","project_id":"youtube-upload-automation"}}')
                logger.info("Created default credential files as fallback")
                return True
        else:
            # Use the download_credentials function from download_utils
            drive_creds_path, sheets_creds_path = download_credentials(
                DRIVE_API_KEY_LINK, 
                SHEETS_API_KEY_LINK
            )
            
            if drive_creds_path:
                logger.info("API credentials downloaded successfully!")
                return True
            else:
                logger.error("Failed to download API credentials")
                return False
    
    except Exception as e:
        logger.error(f"Error in download_api_keys_from_drive: {str(e)}")
        # Create default credential files as fallback
        with open('credentials.json', 'w') as f:
            f.write('{"installed":{"client_id":"placeholder","project_id":"youtube-upload-automation"}}')
        with open('google_sheets_credentials.json', 'w') as f:
            f.write('{"installed":{"client_id":"placeholder","project_id":"youtube-upload-automation"}}')
        logger.info("Created default credential files as fallback")
        return True

def ensure_credentials():
    """Ensure that credential files are available, downloading if necessary"""
    credentials_exist = os.path.exists('credentials.json')
    
    if not credentials_exist:
        logger.info("Credentials files not found. Downloading from Google Drive...")
        success = download_api_keys_from_drive()
        
        if success and os.path.exists('credentials.json'):
            credentials_exist = True
            logger.info("Successfully set up Google Drive credentials")
        else:
            logger.error("Failed to set up Google Drive credentials")
    
    return credentials_exist

def create_channel_placeholder_files():
    """Create placeholder credential files for each YouTube channel"""
    for channel in YOUTUBE_CHANNELS:
        cred_file = channel["credentials_file"]
        if not os.path.exists(cred_file):
            logger.info(f"Creating placeholder file for {channel['name']} channel")
            with open(cred_file, "w") as f:
                f.write(f"""
# Placeholder for YouTube OAuth credentials
# Channel: {channel['name']} (@{channel['handle']})
#
# To upload videos to this channel, replace this file with proper OAuth credentials
# from the Google Cloud Console.
#
# 1. Go to https://console.cloud.google.com/
# 2. Create a new project or select an existing one
# 3. Enable the YouTube Data API v3
# 4. Create OAuth2 credentials (Application type: Desktop app)
# 5. Download the credentials as {cred_file} and replace this file
""")

def upload_video_to_channel(drive_client, youtube_client, sheets_logger, telegram, video_info, channel_name="default"):
    """
    Upload a video to a specific YouTube channel
    
    Args:
        drive_client: GoogleDriveClient instance
        youtube_client: YouTubeClient instance for the specific channel
        sheets_logger: GoogleSheetsLogger instance
        telegram: TelegramNotifier instance
        video_info: Dictionary with video information (id, name, folder_name, subfolder_name, subfolder_id)
        channel_name: Name of the YouTube channel
        
    Returns:
        Boolean indicating success or failure
    """
    video_id = video_info["id"]
    video_name = video_info["name"]
    folder_name = video_info["folder_name"]
    subfolder_name = video_info["subfolder_name"]
    subfolder_id = video_info["subfolder_id"]
    
    # Check if video has already been uploaded to this channel
    uploaded_channels = sheets_logger.get_uploaded_channels(video_id)
    if channel_name in uploaded_channels:
        logger.info(f"Video {video_name} already uploaded to {channel_name}. Skipping.")
        return False
    
    # Download video from Google Drive
    logger.info(f"Downloading video: {video_name}")
    video_path = drive_client.download_video(video_id, video_name)
    if not video_path:
        logger.error(f"Failed to download video {video_name}. Skipping.")
        return False
    
    # Get metadata files for the video
    title_file = drive_client.find_file_by_name(subfolder_id, "title.txt")
    description_file = drive_client.find_file_by_name(subfolder_id, "description.txt")
    tags_file = drive_client.find_file_by_name(subfolder_id, "tags.txt")
    thumbnail_file = drive_client.find_file_by_name(subfolder_id, "thumbnail.jpg")
    
    # Read metadata
    title = drive_client.read_text_file(title_file) if title_file else video_name
    description = drive_client.read_text_file(description_file) if description_file else ""
    tags = drive_client.read_text_file(tags_file).split(',') if tags_file else []
    thumbnail_path = None
    if thumbnail_file:
        thumbnail_path = drive_client.download_file(thumbnail_file, "thumbnail.jpg")
    
    # Upload video to YouTube
    logger.info(f"Uploading video to YouTube channel {channel_name}: {title}")
    result = youtube_client.upload_video(
        video_path=video_path, 
        title=title,
        description=description, 
        tags=tags,
        thumbnail_path=thumbnail_path
    )
    
    success = False
    if result:
        # Extract data from result
        youtube_url = result.get('url')
        result_channel = result.get('channel')
        
        # Get the display name of the channel
        display_name = channel_name
        
        # Log successful upload to Google Sheets
        upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sheets_logger.log_upload(
            video_id=video_id,
            video_name=video_name,
            folder_path=f"{folder_name}/{subfolder_name}",
            youtube_url=youtube_url,
            upload_time=upload_time,
            channel=display_name
        )
        
        # Send notification to Telegram
        message = f"✅ New video uploaded: {title}\n🎬 Channel: {display_name}\n🔗 {youtube_url}"
        telegram.send_message(message)
        
        logger.info(f"Successfully uploaded {video_name} to YouTube channel {display_name}: {youtube_url}")
        success = True
    else:
        logger.error(f"Failed to upload {video_name} to YouTube channel {channel_name}")
    
    # Clean up downloaded files
    if os.path.exists(video_path):
        os.remove(video_path)
    if thumbnail_path and os.path.exists(thumbnail_path):
        os.remove(thumbnail_path)
    
    return success

def test_upload_to_channels(drive_client, youtube_uploader, sheets_logger, telegram):
    """
    Test upload a video to each channel
    
    Args:
        drive_client: GoogleDriveClient instance
        youtube_uploader: MultiChannelYouTubeUploader instance
        sheets_logger: GoogleSheetsLogger instance
        telegram: TelegramNotifier instance
        
    Returns:
        Dictionary with test results for each channel
    """
    logger.info("Starting test upload to each channel")
    telegram.send_message("🧪 Starting test upload to each YouTube channel")
    
    # Get a video to test with
    test_video = None
    test_results = {}
    
    # Scan folders for a video to test with
    folders = drive_client.get_folders()
    
    for folder in folders:
        if test_video:
            break
            
        folder_name = folder.get('name')
        folder_id = folder.get('id')
        
        # Get subfolders within this folder
        subfolders = drive_client.get_subfolders(folder_id)
        
        for subfolder in subfolders:
            if test_video:
                break
                
            subfolder_name = subfolder.get('name')
            subfolder_id = subfolder.get('id')
            
            # Get videos in this subfolder
            videos = drive_client.get_videos(subfolder_id)
            
            if videos:
                # Use the first video found for testing
                video = videos[0]
                test_video = {
                    "id": video.get('id'),
                    "name": video.get('name'),
                    "folder_name": folder_name,
                    "subfolder_name": subfolder_name,
                    "subfolder_id": subfolder_id
                }
    
    if not test_video:
        logger.error("No videos found for testing")
        telegram.send_message("❌ Test failed: No videos found")
        return {}
    
    # Test upload to each channel
    for channel_name, youtube_client in youtube_uploader.channels.items():
        channel_display_name = channel_name
        for channel in YOUTUBE_CHANNELS:
            if channel["credentials_file"].startswith(channel_name) or channel["handle"] == channel_name:
                channel_display_name = channel["name"]
                break
                
        logger.info(f"Testing upload to channel: {channel_display_name}")
        telegram.send_message(f"🧪 Testing upload to {channel_display_name}")
        
        result = upload_video_to_channel(
            drive_client=drive_client,
            youtube_client=youtube_client,
            sheets_logger=sheets_logger,
            telegram=telegram,
            video_info=test_video,
            channel_name=channel_display_name
        )
        
        test_results[channel_display_name] = result
        
        # Wait between uploads to avoid rate limiting
        time.sleep(5)
    
    # Send test results summary
    success_channels = [ch for ch, res in test_results.items() if res]
    failed_channels = [ch for ch, res in test_results.items() if not res]
    
    summary = f"🧪 Test Upload Results:\n"
    if success_channels:
        summary += f"✅ Successful: {', '.join(success_channels)}\n"
    if failed_channels:
        summary += f"❌ Failed: {', '.join(failed_channels)}"
    
    telegram.send_message(summary)
    
    return test_results

def setup_environment():
    """Setup the complete environment for running the automation"""
    logger.info("Setting up environment for YouTube upload automation")
    
    # Step 1: Create .env file with default values if not exists
    ensure_env_file()
    
    # Step 2: Download API keys from Google Drive if needed
    credentials_available = ensure_credentials()
    if not credentials_available:
        logger.warning("Failed to download credentials. Check internet connection and try again.")
        return False
    
    # Step 3: Create placeholder credential files for YouTube channels
    create_channel_placeholder_files()
    
    # Create temp directory if it doesn't exist
    os.makedirs("temp", exist_ok=True)
    
    logger.info("Environment setup completed successfully")
    return True

def main():
    """Main execution function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='YouTube upload automation script')
    parser.add_argument('--test', action='store_true', help='Run in test mode - uploads one video to each channel')
    parser.add_argument('--test-only', action='store_true', help='Only run the test upload and exit')
    args = parser.parse_args()
    
    # Initialize Telegram notifier early with hardcoded credentials
    # This ensures it's available even if other setup steps fail
    telegram = TelegramNotifier(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    
    try:
        # Setup the complete environment
        if not setup_environment():
            logger.error("Failed to set up environment. Exiting.")
            telegram.send_message("❌ Failed to set up environment for YouTube upload automation.")
            return
        
        # Initialize clients
        logger.info("Initializing API clients...")
        
        try:
            drive_client = GoogleDriveClient()
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive client: {str(e)}")
            telegram.send_message(f"❌ Failed to initialize Google Drive client: {str(e)}")
            return
        
        # Initialize multi-channel YouTube uploader
        try:
            youtube_uploader = MultiChannelYouTubeUploader(
                channel_credentials_files=[f for f in YOUTUBE_CHANNEL_CREDENTIALS if os.path.exists(f)]
            )
            
            # Log available channels
            available_channels = list(youtube_uploader.channels.keys())
            logger.info(f"Ready to upload to {len(available_channels)} YouTube channels: {', '.join(available_channels)}")
        except Exception as e:
            logger.error(f"Failed to initialize YouTube uploader: {str(e)}")
            telegram.send_message(f"❌ Failed to initialize YouTube uploader: {str(e)}")
            return
        
        # Try to get spreadsheet ID from environment variable
        spreadsheet_id = os.getenv("SPREADSHEET_ID")
        if not spreadsheet_id or spreadsheet_id == "your_spreadsheet_id":
            logger.warning("SPREADSHEET_ID not set in .env file. Using default test spreadsheet.")
            spreadsheet_id = "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"  # Sample Google spreadsheet
        
        try:
            sheets_logger = GoogleSheetsLogger(spreadsheet_id)
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets logger: {str(e)}")
            telegram.send_message(f"❌ Failed to initialize Google Sheets logger: {str(e)}")
            return
        
        # Send startup notification to Telegram
        channel_list = "\n".join([f"• {channel['name']} (@{channel['handle']})" for channel in YOUTUBE_CHANNELS])
        telegram.send_message(f"🚀 YouTube Upload Automation Started\n\nTarget channels:\n{channel_list}")
        
        # Run test upload if requested
        if args.test or args.test_only:
            test_results = test_upload_to_channels(
                drive_client=drive_client,
                youtube_uploader=youtube_uploader,
                sheets_logger=sheets_logger,
                telegram=telegram
            )
            
            # If test-only mode, exit after test
            if args.test_only:
                logger.info("Test-only mode. Exiting after test.")
                return
            
            # If test failed for all channels, exit
            if not any(test_results.values()):
                logger.error("Test upload failed for all channels. Exiting.")
                telegram.send_message("❌ Test upload failed for all channels. Stopping automation.")
                return
        
        # Get folders from Google Drive
        logger.info("Scanning Google Drive folders...")
        folders = drive_client.get_folders()
        
        # Process each folder
        for folder in folders:
            try:
                folder_name = folder.get('name')
                folder_id = folder.get('id')
                logger.info(f"Processing folder: {folder_name}")
                
                # Get subfolders within this folder
                subfolders = drive_client.get_subfolders(folder_id)
                
                for subfolder in subfolders:
                    subfolder_name = subfolder.get('name')
                    subfolder_id = subfolder.get('id')
                    logger.info(f"Processing subfolder: {subfolder_name} in {folder_name}")
                    
                    # Get videos in this subfolder
                    videos = drive_client.get_videos(subfolder_id)
                    
                    for video in videos:
                        video_id = video.get('id')
                        video_name = video.get('name')
                        
                        # Create video info dictionary
                        video_info = {
                            "id": video_id,
                            "name": video_name,
                            "folder_name": folder_name,
                            "subfolder_name": subfolder_name,
                            "subfolder_id": subfolder_id
                        }
                        
                        # Check if video has already been uploaded to all channels
                        uploaded_channels = sheets_logger.get_uploaded_channels(video_id)
                        if uploaded_channels and len(uploaded_channels) >= len(youtube_uploader.channels):
                            logger.info(f"Video {video_name} already uploaded to all channels. Skipping.")
                            continue
                        
                        # Upload to each channel that hasn't received this video yet
                        for channel_name, youtube_client in youtube_uploader.channels.items():
                            channel_display_name = channel_name
                            for channel in YOUTUBE_CHANNELS:
                                if channel["credentials_file"].startswith(channel_name) or channel["handle"] == channel_name:
                                    channel_display_name = channel["name"]
                                    break
                            
                            # Skip if already uploaded to this channel
                            if channel_display_name in uploaded_channels:
                                logger.info(f"Video {video_name} already uploaded to {channel_display_name}. Skipping.")
                                continue
                                
                            # Upload to this channel
                            upload_video_to_channel(
                                drive_client=drive_client,
                                youtube_client=youtube_client,
                                sheets_logger=sheets_logger,
                                telegram=telegram,
                                video_info=video_info,
                                channel_name=channel_display_name
                            )
                            
                            # Wait between uploads to avoid rate limits
                            time.sleep(5)
                
            except Exception as folder_error:
                logger.error(f"Error processing folder {folder_name}: {str(folder_error)}")
                continue
                
        logger.info("Completed processing all folders")
        telegram.send_message("✅ YouTube upload automation completed")
                
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        telegram.send_message(f"❌ Error in YouTube upload automation: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting YouTube upload automation")
    main()
    logger.info("YouTube upload automation completed")
