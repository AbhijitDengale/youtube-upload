"""
Telegram bot utility functions for sending notifications.
"""

import logging
import requests
import time

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Class for sending notifications via Telegram Bot API"""
    
    def __init__(self, bot_token, chat_id):
        """
        Initialize Telegram notifier with bot token and chat ID.
        
        Args:
            bot_token: Telegram bot token
            chat_id: Telegram chat ID (user or group) to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        
        # Check if token and chat_id are provided
        if not bot_token:
            logger.warning("Telegram bot token not provided. Notifications will not be sent.")
        if not chat_id:
            logger.warning("Telegram chat ID not provided. Notifications will not be sent.")
            
        # Test the connection
        if bot_token and chat_id:
            self.test_connection()
    
    def test_connection(self):
        """Test the Telegram bot connection"""
        try:
            url = f"{self.base_url}/getMe"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data["ok"]:
                    bot_name = data["result"]["username"]
                    logger.info(f"Connected to Telegram bot: {bot_name}")
                    return True
                else:
                    logger.error(f"Failed to connect to Telegram bot: {data.get('description')}")
            else:
                logger.error(f"HTTP error when connecting to Telegram: {response.status_code}")
            return False
        except Exception as e:
            logger.error(f"Error testing Telegram connection: {str(e)}")
            return False
    
    def send_message(self, message, retry_count=3, retry_delay=5):
        """
        Send a message to the specified chat ID.
        
        Args:
            message: Message text to send
            retry_count: Number of retries if sending fails
            retry_delay: Delay between retries in seconds
            
        Returns:
            Boolean indicating success or failure
        """
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram notification skipped: missing bot token or chat ID")
            return False
            
        url = f"{self.base_url}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': False
        }
        
        for attempt in range(retry_count):
            try:
                response = requests.post(url, data=payload)
                if response.status_code == 200:
                    logger.info("Message sent successfully to Telegram")
                    return True
                else:
                    logger.warning(f"Failed to send Telegram message, status: {response.status_code}, response: {response.text}")
                    if attempt < retry_count - 1:
                        logger.info(f"Retrying in {retry_delay} seconds... (Attempt {attempt+1}/{retry_count})")
                        time.sleep(retry_delay)
            except Exception as e:
                logger.error(f"Error sending Telegram message: {str(e)}")
                if attempt < retry_count - 1:
                    logger.info(f"Retrying in {retry_delay} seconds... (Attempt {attempt+1}/{retry_count})")
                    time.sleep(retry_delay)
        
        return False
    
    def send_photo(self, photo_path, caption=None, retry_count=3, retry_delay=5):
        """
        Send a photo to the specified chat ID.
        
        Args:
            photo_path: Path to the photo file
            caption: Optional caption for the photo
            retry_count: Number of retries if sending fails
            retry_delay: Delay between retries in seconds
            
        Returns:
            Boolean indicating success or failure
        """
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram photo notification skipped: missing bot token or chat ID")
            return False
            
        url = f"{self.base_url}/sendPhoto"
        payload = {
            'chat_id': self.chat_id
        }
        
        if caption:
            payload['caption'] = caption
        
        for attempt in range(retry_count):
            try:
                with open(photo_path, 'rb') as photo:
                    response = requests.post(url, data=payload, files={'photo': photo})
                
                if response.status_code == 200:
                    logger.info("Photo sent successfully to Telegram")
                    return True
                else:
                    logger.warning(f"Failed to send Telegram photo, status: {response.status_code}, response: {response.text}")
                    if attempt < retry_count - 1:
                        logger.info(f"Retrying in {retry_delay} seconds... (Attempt {attempt+1}/{retry_count})")
                        time.sleep(retry_delay)
            except Exception as e:
                logger.error(f"Error sending Telegram photo: {str(e)}")
                if attempt < retry_count - 1:
                    logger.info(f"Retrying in {retry_delay} seconds... (Attempt {attempt+1}/{retry_count})")
                    time.sleep(retry_delay)
        
        return False
