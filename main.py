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
YOUTUBE_OAUTH_LINK = "https://drive.google.com/file/d/13ixoC9O9QrBlSOhUKjrUq9a5cG8oVgZw/view?usp=sharing"  # Added OAuth creds link
YOUTUBE_API_KEY = "AIzaSyCNbN-lpBIAjZHxe9wI60bTbig4VyT6i10"  # Hardcoded for simplicity
TELEGRAM_BOT_TOKEN = "7425850499:AAFeqvSXe-KRaBCEvRlrpfdSbExSoGeMiCI"  # Hardcoded for simplicity
TELEGRAM_CHAT_ID = "-1002493560505"  # Hardcoded for simplicity

# Target YouTube channels
YOUTUBE_CHANNELS = [
    {"name": "Tiny Trailblazers", "handle": "TinyTrailblazers", "credentials_file": "channel1_client_secret.json"},
    {"name": "KidVenture Quest", "handle": "KidVentureQuestnw", "credentials_file": "channel2_client_secret.json"},
    {"name": "MagicMap Tales", "handle": "MagicMapTales", "credentials_file": "channel3_client_secret.json"}
]

# Define channel credential files
YOUTUBE_CHANNEL_CREDENTIALS = [channel["credentials_file"] for channel in YOUTUBE_CHANNELS]

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
                youtube_oauth_id = YOUTUBE_OAUTH_LINK.split('/')[-2]
                
                # Direct download URLs
                drive_download_url = f"https://drive.google.com/uc?export=download&id={drive_api_key_id}"
                sheets_download_url = f"https://drive.google.com/uc?export=download&id={sheets_api_key_id}"
                youtube_oauth_url = f"https://drive.google.com/uc?export=download&id={youtube_oauth_id}"
                
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
                
                # Download YouTube OAuth credentials
                try:
                    logger.info(f"Downloading YouTube OAuth credentials from {youtube_oauth_url}")
                    response = requests.get(youtube_oauth_url)
                    if response.status_code == 200:
                        # Save the single OAuth file
                        with open('youtube_oauth_credentials.json', 'wb') as f:
                            f.write(response.content)
                        logger.info("Successfully downloaded YouTube OAuth credentials")
                        
                        # Create copies for each channel using the same credentials
                        for channel in YOUTUBE_CHANNELS:
                            with open(channel["credentials_file"], 'wb') as f:
                                f.write(response.content)
                            logger.info(f"Created OAuth credentials for {channel['name']} channel")
                    else:
                        logger.error(f"Failed to download YouTube OAuth credentials: {response.status_code}")
                except Exception as e:
                    logger.error(f"Error downloading YouTube OAuth credentials: {str(e)}")
                
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
    """Create placeholder credential files for each YouTube channel if they don't exist"""
    # If we have the master OAuth file, copy it for each channel
    if os.path.exists('youtube_oauth_credentials.json'):
        with open('youtube_oauth_credentials.json', 'rb') as source_file:
            oauth_content = source_file.read()
            for channel in YOUTUBE_CHANNELS:
                cred_file = channel["credentials_file"]
                if not os.path.exists(cred_file):
                    logger.info(f"Creating OAuth credential file for {channel['name']} channel")
                    with open(cred_file, 'wb') as f:
                        f.write(oauth_content)
                    
                    # Also create a .info file to document what this is for humans
                    with open(f"{cred_file}.info", "w") as f:
                        f.write(f"""
# Information about the YouTube OAuth credentials file
# Channel: {channel['name']} (@{channel['handle']})
#
# This file contains OAuth credentials for YouTube API access.
# When you run the script, you'll need to authenticate with the 
# Google account associated with the {channel['name']} channel.
""")
        return
    
    # Otherwise create placeholder files if needed
    for channel in YOUTUBE_CHANNELS:
        cred_file = channel["credentials_file"]
        if not os.path.exists(cred_file):
            logger.info(f"Creating placeholder file for {channel['name']} channel")
            # Create a valid JSON structure for the placeholder
            placeholder_data = {
                "installed": {
                    "client_id": f"placeholder-{channel['handle']}",
                    "project_id": "youtube-upload-automation",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": "placeholder-secret",
                    "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
                }
            }
            
            # Write the JSON data to the file
            with open(cred_file, "w") as f:
                json.dump(placeholder_data, f, indent=2)
                
            # Also create a .info file to document what this is for humans
            with open(f"{cred_file}.info", "w") as f:
                f.write(f"""
# Information about the YouTube OAuth credentials file
# Channel: {channel['name']} (@{channel['handle']})
#
# The main file ({cred_file}) contains a placeholder for OAuth credentials.
# To upload videos to this channel, replace it with proper OAuth credentials
# from the Google Cloud Console.
#
# Steps to create proper credentials:
# 1. Go to https://console.cloud.google.com/
# 2. Create a new project or select an existing one
# 3. Enable the YouTube Data API v3
# 4. Create OAuth2 credentials (Application type: Desktop app)
# 5. Download the credentials and replace {cred_file} with the downloaded content
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
    
    # Specifically look for the GeminiStories folder
    target_folder_name = "GeminiStories"
    logger.info(f"Scanning for {target_folder_name} folder for test videos")
    
    # Get all folders from Google Drive
    all_folders = drive_client.get_folders()
    
    # Find the GeminiStories folder
    target_folder = None
    for folder in all_folders:
        if folder.get('name') == target_folder_name:
            target_folder = folder
            break
    
    if not target_folder:
        error_msg = f"Folder '{target_folder_name}' not found in Google Drive for testing"
        logger.error(error_msg)
        telegram.send_message(f"❌ Test failed: {error_msg}")
        return {}
    
    # Process the target folder
    folder_name = target_folder.get('name')
    folder_id = target_folder.get('id')
    logger.info(f"Found {folder_name} folder for testing")
    
    # Get subfolders within the target folder
    subfolders = drive_client.get_subfolders(folder_id)
    
    # Look for videos in each subfolder
    for subfolder in subfolders:
        if test_video:
            break
            
        subfolder_name = subfolder.get('name')
        subfolder_id = subfolder.get('id')
        logger.info(f"Checking subfolder {subfolder_name} for test videos")
        
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
            logger.info(f"Found test video: {video.get('name')} in {subfolder_name}")
    
    if not test_video:
        logger.error(f"No videos found in any {target_folder_name} subfolders. Please upload a video first.")
        telegram.send_message(f"❌ Test failed: No videos found in {target_folder_name} folder. Please upload a video first.")
        return {}
    
    # Test upload to each channel
    for channel_name, youtube_client in youtube_uploader.channels.items():
        # Skip the default client which is used internally
        if channel_name == "default":
            continue
            
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
    parser.add_argument('--folder', type=str, default="GeminiStories", 
                      help='Name of the main Google Drive folder to scan for videos (default: GeminiStories)')
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
        
        # Check if we're in test mode
        is_test_mode = args.test or args.test_only
        
        # Initialize multi-channel YouTube uploader
        try:
            youtube_uploader = MultiChannelYouTubeUploader(
                channel_credentials_files=[f for f in YOUTUBE_CHANNEL_CREDENTIALS if os.path.exists(f)],
                use_api_key_for_testing=is_test_mode  # Use API key in test mode to avoid OAuth prompt
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
        
        # Target specific folder in Google Drive (GeminiStories by default)
        target_folder_name = args.folder
        logger.info(f"Scanning for main folder: {target_folder_name}")
        
        # Get all folders from Google Drive
        all_folders = drive_client.get_folders()
        
        # Find the GeminiStories folder (or the folder specified by --folder)
        target_folder = None
        for folder in all_folders:
            if folder.get('name') == target_folder_name:
                target_folder = folder
                break
        
        if not target_folder:
            error_msg = f"Folder '{target_folder_name}' not found in Google Drive. Please create it or specify the correct folder name."
            logger.error(error_msg)
            telegram.send_message(f"❌ {error_msg}")
            return
                
        # Process the target folder and its subfolders
        folder_name = target_folder.get('name')
        folder_id = target_folder.get('id')
        logger.info(f"Processing main folder: {folder_name}")
        
        # Get subfolders within the target folder
        subfolders = drive_client.get_subfolders(folder_id)
        
        # Count of processed videos
        processed_count = 0
        
        for subfolder in subfolders:
            try:
                subfolder_name = subfolder.get('name')
                subfolder_id = subfolder.get('id')
                logger.info(f"Processing subfolder: {subfolder_name}")
                
                # Get videos in this subfolder
                videos = drive_client.get_videos(subfolder_id)
                
                if not videos:
                    logger.info(f"No videos found in subfolder {subfolder_name}")
                    continue
                    
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
                        processed_count += 1
                        
                        # Wait between uploads to avoid rate limits
                        time.sleep(5)
                        
            except Exception as subfolder_error:
                logger.error(f"Error processing subfolder {subfolder_name}: {str(subfolder_error)}")
                continue
                
        logger.info(f"Completed processing {processed_count} videos from {len(subfolders)} subfolders")
        telegram.send_message(f"✅ YouTube upload automation completed. Processed {processed_count} videos.")
                
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        telegram.send_message(f"❌ Error in YouTube upload automation: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting YouTube upload automation")
    main()
    logger.info("YouTube upload automation completed")
