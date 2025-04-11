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
