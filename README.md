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

You can run this automation in Google Colab with just a few simple steps! The code now handles all setup automatically.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/AbhijitDengale/youtube-upload/blob/master/youtube_upload_automation.ipynb)

### Quick Start (Two Steps!)

```python
# 1. Clone the repository and navigate to it
!git clone https://github.com/AbhijitDengale/youtube-upload.git
%cd youtube-upload

# 2. Install dependencies and run in test mode
!pip install -r requirements.txt
!python main.py --test-only
```

That's it! The script will automatically:
- Download the API keys from Google Drive
- Create necessary configuration files
- Set up YouTube channel placeholders
- Find a video to test with
- Upload it to each channel
- Send Telegram notifications
- Log the uploads in Google Sheets

### Viewing the Results

```python
# View the logs to see what happened
!cat upload_logs.log
```

### Important Notes for Google Colab:

1. **OAuth Authentication**: When running in Colab, the YouTube API OAuth flow will open a separate authentication window. You'll need to complete the authentication process for each channel.

2. **Persistence**: Colab sessions are temporary. If you want to keep the credentials, download them before closing the session.

3. **Rate Limits**: Be aware of API rate limits when testing multiple uploads.

4. **Runtime**: Colab may disconnect if the script runs for too long. Consider using shorter timeouts for testing.
