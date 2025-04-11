"""
YouTube API utility functions for the YouTube upload automation system.
"""

import os
import http.client
import httplib2
import random
import time
import logging
import argparse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run_flow, argparser

logger = logging.getLogger(__name__)

# Hardcoded YouTube API Key
YOUTUBE_API_KEY = "AIzaSyCNbN-lpBIAjZHxe9wI60bTbig4VyT6i10"

# This OAuth 2.0 access scope allows an application to upload files to the
# authenticated user's YouTube channel, but doesn't allow other types of access.
YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]
YOUTUBE_API_SERVICE_NAME = "youtube"
YOUTUBE_API_VERSION = "v3"

# This variable defines a message to display if the CLIENT_SECRETS_FILE is missing.
MISSING_CLIENT_SECRETS_MESSAGE = """
WARNING: Please configure OAuth 2.0

To make this sample run you will need to populate the client_secrets.json file
found at:

   %s

with information from the API Console
https://console.cloud.google.com/

For more information about the client_secrets.json file format, please visit:
https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
"""

# Explicitly tell the underlying HTTP transport library not to retry, since
# we are handling retry logic ourselves.
httplib2.RETRIES = 1

# Maximum number of times to retry before giving up.
MAX_RETRIES = 10

# Always retry when these exceptions are raised.
RETRIABLE_EXCEPTIONS = (httplib2.HttpLib2Error, IOError, http.client.NotConnected,
                        http.client.IncompleteRead, http.client.ImproperConnectionState,
                        http.client.CannotSendRequest, http.client.CannotSendHeader,
                        http.client.ResponseNotReady, http.client.BadStatusLine)

# Always retry when an apiclient.errors.HttpError with one of these status
# codes is raised.
RETRIABLE_STATUS_CODES = [500, 502, 503, 504]

class YouTubeClient:
    """Client for interacting with YouTube API"""
    
    def __init__(self, channel_credentials_file=None):
        """
        Initialize the YouTube API client
        
        Args:
            channel_credentials_file: Optional path to a channel-specific OAuth credentials file
        """
        try:
            self.channel_name = "default"
            
            # Check if we have client secrets file for OAuth for this specific channel
            if channel_credentials_file and os.path.exists(channel_credentials_file):
                self._initialize_with_oauth(channel_credentials_file)
                self.channel_name = os.path.basename(channel_credentials_file).split('.')[0]
            elif os.path.exists('client_secret.json'):
                self._initialize_with_oauth('client_secret.json')
            else:
                # Use hardcoded API key instead (with limited functionality)
                self.youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, 
                                     developerKey=YOUTUBE_API_KEY)
            
            logger.info(f"YouTube API client initialized successfully for channel: {self.channel_name}")
        except Exception as e:
            logger.error(f"Error initializing YouTube client: {str(e)}")
            raise
    
    def _initialize_with_oauth(self, client_secrets_file):
        """
        Initialize YouTube API with OAuth authentication
        
        Args:
            client_secrets_file: Path to client secrets file
        """
        # Generate a unique credentials file name based on the client_secrets_file name
        credentials_file = f"youtube-oauth2-{os.path.basename(client_secrets_file).split('.')[0]}.json"
        
        flow = flow_from_clientsecrets(
            client_secrets_file,
            scope=YOUTUBE_UPLOAD_SCOPE,
            message=MISSING_CLIENT_SECRETS_MESSAGE % client_secrets_file
        )
        
        storage = Storage(credentials_file)
        credentials = storage.get()
        
        if credentials is None or credentials.invalid:
            logger.info(f"Obtaining new OAuth credentials for {client_secrets_file}")
            # Create a separate parser for OAuth flow to prevent conflicts with main script
            oauth_parser = argparse.ArgumentParser(parents=[argparser])
            oauth_args = oauth_parser.parse_args([])  # Empty list to avoid reading sys.argv
            
            # Pass the custom arguments to avoid conflict with main script arguments
            credentials = run_flow(flow, storage, oauth_args)
        
        self.youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, 
                           credentials=credentials)
    
    def _wait_for_rate_limit_reset(self, seconds_to_wait=10):
        """Wait for YouTube API rate limit to reset"""
        logger.info(f"Hit YouTube API rate limit. Waiting {seconds_to_wait} seconds...")
        time.sleep(seconds_to_wait)
    
    def upload_video(self, video_path, title, description="", tags=None, 
                    category=22, privacy_status="public", thumbnail_path=None):
        """
        Upload a video to YouTube.
        
        Args:
            video_path: Path to the video file
            title: Video title
            description: Video description
            tags: List of tags for the video
            category: Video category ID (default=22, which is 'People & Blogs')
            privacy_status: Privacy status (public, private, unlisted)
            thumbnail_path: Path to thumbnail image file (optional)
            
        Returns:
            Dictionary with YouTube URL and channel information of the uploaded video, 
            or None if upload fails
        """
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None
            
        if tags is None:
            tags = []
            
        body = {
            "snippet": {
                "title": title,
                "description": description,
                "tags": tags,
                "categoryId": category
            },
            "status": {
                "privacyStatus": privacy_status
            }
        }
        
        # Call the API's videos.insert method to create and upload the video.
        try:
            # Log the actual upload
            logger.info(f"Uploading {video_path} to YouTube channel: {self.channel_name}...")
            
            # The chunksize parameter specifies the size of each chunk of data, in
            # bytes, that will be uploaded at a time. Set a higher value for
            # reliable connections as fewer chunks lead to faster uploads. Set a lower
            # value for better recovery on less reliable connections.
            #
            # Setting "resumable=True" enables resumable uploads.
            insert_request = self.youtube.videos().insert(
                part=",".join(body.keys()),
                body=body,
                media_body=MediaFileUpload(
                    video_path, 
                    chunksize=10*1024*1024, 
                    resumable=True
                )
            )
            
            video_id = self._resumable_upload(insert_request)
            
            if not video_id:
                logger.error("Failed to upload video")
                return None
                
            # Set thumbnail if provided
            if thumbnail_path and os.path.exists(thumbnail_path):
                self.set_thumbnail(video_id, thumbnail_path)
                
            youtube_url = f"https://www.youtube.com/watch?v={video_id}"
            logger.info(f"Video uploaded successfully to channel {self.channel_name}: {youtube_url}")
            
            # Return both URL and channel information
            return {
                "url": youtube_url,
                "video_id": video_id,
                "channel": self.channel_name
            }
            
        except HttpError as e:
            logger.error(f"An HTTP error {e.resp.status} occurred: {e.content}")
            return None
        except Exception as e:
            logger.error(f"Error uploading video: {str(e)}")
            return None
    
    def _resumable_upload(self, insert_request):
        """
        Implements resumable upload to YouTube.
        
        Args:
            insert_request: The YouTube video insert request
            
        Returns:
            The ID of the uploaded video if successful, None otherwise
        """
        response = None
        error = None
        retry = 0
        
        while response is None:
            try:
                logger.info("Uploading file...")
                status, response = insert_request.next_chunk()
                if response is not None:
                    if 'id' in response:
                        logger.info(f"Video ID '{response['id']}' was successfully uploaded.")
                        return response['id']
                    else:
                        logger.error(f"The upload failed with an unexpected response: {response}")
                        return None
            except HttpError as e:
                if e.resp.status in RETRIABLE_STATUS_CODES:
                    error = f"A retriable HTTP error {e.resp.status} occurred: {e.content}"
                else:
                    raise
            except RETRIABLE_EXCEPTIONS as e:
                error = f"A retriable error occurred: {e}"
            
            if error is not None:
                logger.error(error)
                retry += 1
                if retry > MAX_RETRIES:
                    logger.error("No longer attempting to retry.")
                    return None
                
                max_sleep = 2 ** retry
                sleep_seconds = random.random() * max_sleep
                logger.info(f"Sleeping {sleep_seconds} seconds and then retrying...")
                time.sleep(sleep_seconds)
    
    def set_thumbnail(self, video_id, thumbnail_path):
        """Set a custom thumbnail for a video"""
        try:
            logger.info(f"Setting thumbnail for video {video_id}")
            self.youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path)
            ).execute()
            logger.info("Thumbnail set successfully")
            return True
        except HttpError as e:
            logger.error(f"An HTTP error {e.resp.status} occurred while setting thumbnail: {e.content}")
            return False
        except Exception as e:
            logger.error(f"Error setting thumbnail: {str(e)}")
            return False

class MultiChannelYouTubeUploader:
    """Class for uploading videos to multiple YouTube channels"""
    
    def __init__(self, channel_credentials_files=None):
        """
        Initialize multiple YouTube clients for different channels
        
        Args:
            channel_credentials_files: List of paths to channel-specific OAuth credential files
        """
        self.channels = {}
        
        # Initialize default channel with API key
        self.channels["default"] = YouTubeClient()
        
        # Initialize additional channels if credentials files are provided
        if channel_credentials_files:
            for credentials_file in channel_credentials_files:
                if os.path.exists(credentials_file):
                    client = YouTubeClient(credentials_file)
                    self.channels[client.channel_name] = client
        
        logger.info(f"Initialized YouTube uploader with {len(self.channels)} channels: {', '.join(self.channels.keys())}")
    
    def upload_to_all_channels(self, video_path, title, description="", tags=None, 
                              category=22, privacy_status="public", thumbnail_path=None):
        """
        Upload a video to all configured YouTube channels
        
        Args:
            video_path: Path to the video file
            title: Video title
            description: Video description
            tags: List of tags for the video
            category: Video category ID
            privacy_status: Privacy status
            thumbnail_path: Path to thumbnail image file
            
        Returns:
            List of dictionaries with upload results for each channel
        """
        results = []
        
        for channel_name, client in self.channels.items():
            logger.info(f"Uploading to channel: {channel_name}")
            
            result = client.upload_video(
                video_path=video_path,
                title=title,
                description=description,
                tags=tags,
                category=category,
                privacy_status=privacy_status,
                thumbnail_path=thumbnail_path
            )
            
            if result:
                results.append(result)
            
            # Wait between uploads to avoid rate limiting
            time.sleep(5)
        
        return results
