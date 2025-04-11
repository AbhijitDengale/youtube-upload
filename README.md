# YouTube Upload Automation

This project automates the process of uploading videos from Google Drive to YouTube, sending notifications via Telegram, and logging uploads in Google Sheets.

## Features

- Monitors Google Drive folders for videos
- Uploads videos to YouTube using the YouTube Data API
- Sends notification messages to Telegram when uploads are successful
- Logs uploaded videos in Google Sheets to prevent duplicate uploads

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure API credentials in `.env` file:
   ```
   GOOGLE_DRIVE_API_KEY=your_drive_api_key
   YOUTUBE_API_KEY=your_youtube_api_key
   GOOGLE_SHEETS_API_KEY=your_sheets_api_key
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   TELEGRAM_CHAT_ID=your_telegram_chat_id
   SPREADSHEET_ID=your_google_spreadsheet_id
   ```

3. Run the script:
   ```
   python main.py
   ```

## Running in Test Mode

You can run the script in test mode to upload just one video to each channel:

```
python main.py --test-only
```

This will:
1. Find a video in your Google Drive
2. Upload it to each configured YouTube channel
3. Send notifications via Telegram
4. Log the uploads in Google Sheets

## Google Colab Setup

You can run this automation in Google Colab for testing purposes. Here's how to set it up:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AbhijitDengale/youtube-upload/blob/master/youtube_upload_automation.ipynb)

### 1. Clone the GitHub Repository

```python
# Clone the repository
!git clone https://github.com/AbhijitDengale/youtube-upload.git
%cd youtube-upload
```

### 2. Install Required Dependencies

```python
# Install required packages
!pip install -r requirements.txt
```

### 3. Download API Keys from Google Drive

```python
# Import required libraries
import os
import requests
import io
from google.colab import auth
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import google.auth

# Authenticate with Google
auth.authenticate_user()
credentials, project_id = google.auth.default()

# Function to download file from Google Drive
def download_file_from_drive(file_id, output_path):
    """Download a file from Google Drive using its file ID"""
    drive_service = build('drive', 'v3', credentials=credentials)
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.FileIO(output_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
        print(f"Download {int(status.progress() * 100)}%")
    return output_path

# Download API keys (replace with your actual file IDs)
drive_api_key_id = "152LtocR_Lvll37IW3GXJWAowLS02YBF2"  # From the shared link
sheets_api_key_id = "1W365AG3tpzytNRnZ9darqLDLx94XYsNo"  # From the shared link

# Download the files
download_file_from_drive(drive_api_key_id, "credentials.json")
download_file_from_drive(sheets_api_key_id, "google_sheets_credentials.json")

print("API credentials downloaded successfully!")
```

### 4. Create .env File with Your Configuration

```python
# Create .env file with your credentials
%%writefile .env
GOOGLE_DRIVE_API_KEY=your_drive_api_key
YOUTUBE_API_KEY=AIzaSyCNbN-lpBIAjZHxe9wI60bTbig4VyT6i10
GOOGLE_SHEETS_API_KEY=your_sheets_api_key
SPREADSHEET_ID=your_spreadsheet_id
TELEGRAM_BOT_TOKEN=7425850499:AAFeqvSXe-KRaBCEvRlrpfdSbExSoGeMiCI
TELEGRAM_CHAT_ID=-1002493560505
```

### 5. Create OAuth Credential Placeholders for YouTube Channels

```python
# Create placeholder OAuth credentials for the three channels
channel_info = [
    {"name": "Tiny Trailblazers", "handle": "TinyTrailblazers", "file": "channel1_client_secret.json"},
    {"name": "KidVenture Quest", "handle": "KidVentureQuestnw", "file": "channel2_client_secret.json"},
    {"name": "MagicMap Tales", "handle": "MagicMapTales", "file": "channel3_client_secret.json"}
]

for channel in channel_info:
    with open(channel["file"], "w") as f:
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
# 5. Download the credentials as {channel["file"]} and replace this file
""")
    print(f"Created placeholder for {channel['name']}")
```

### 6. Run in Test Mode

```python
# Run the script in test mode
!python main.py --test-only
```

### 7. View the Logs

```python
# View the logs to see what happened
!cat upload_logs.log
```

### Important Notes for Google Colab:

1. **OAuth Authentication**: When running in Colab, the YouTube API OAuth flow will open a separate authentication window. You'll need to complete the authentication process for each channel.

2. **Persistence**: Colab sessions are temporary. If you want to keep the credentials, download them before closing the session.

3. **Rate Limits**: Be aware of API rate limits when testing multiple uploads.

4. **Runtime**: Colab may disconnect if the script runs for too long. Consider using shorter timeouts for testing.
