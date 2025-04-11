#!/usr/bin/env python3
"""
Google Drive Explorer

This script explores the complete structure of a Google Drive account,
showing folder hierarchies and contents to help identify where videos are stored.
"""

import os
import sys
import logging
import argparse
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('drive_explore.log')
    ]
)
logger = logging.getLogger(__name__)

def build_drive_service():
    """Initialize Google Drive API client"""
    try:
        # Check if using API key or OAuth credentials
        if os.path.exists('credentials.json'):
            logger.info("Using credentials.json for Drive authentication")
            creds = service_account.Credentials.from_service_account_file(
                'credentials.json',
                scopes=['https://www.googleapis.com/auth/drive.readonly']
            )
        else:
            # Using API key
            api_key = os.getenv('GOOGLE_DRIVE_API_KEY')
            if not api_key:
                raise ValueError("Google Drive API key not found in environment variables")
            logger.info("Using API key for Drive authentication")
            return build('drive', 'v3', developerKey=api_key)
            
        service = build('drive', 'v3', credentials=creds)
        logger.info("Google Drive API client initialized successfully")
        return service
    except Exception as e:
        logger.error(f"Error initializing Google Drive client: {str(e)}")
        raise

def get_folder_contents(service, folder_id='root', depth=0, max_depth=3, path=""):
    """Recursively list contents of a folder"""
    indent = "  " * depth
    current_path = f"{path} > {get_item_name(service, folder_id)}" if path else get_item_name(service, folder_id)
    
    # Print current folder info
    logger.info(f"{indent}📁 FOLDER: {current_path} (ID: {folder_id})")
    
    # If we've reached max depth, stop recursing
    if depth >= max_depth:
        logger.info(f"{indent}  [Max depth reached. Stopping recursion at {current_path}]")
        return
    
    try:
        # Get all items in this folder
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, mimeType, size)"
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            logger.info(f"{indent}  [Empty folder]")
            return
        
        # Sort items - folders first, then files
        folders = [item for item in items if item.get('mimeType') == 'application/vnd.google-apps.folder']
        files = [item for item in items if item.get('mimeType') != 'application/vnd.google-apps.folder']
        
        # Process folders first
        for folder in folders:
            # Recursively process this folder
            get_folder_contents(
                service, 
                folder.get('id'), 
                depth + 1, 
                max_depth, 
                current_path
            )
        
        # Then list files
        if files:
            logger.info(f"{indent}  Files in {get_item_name(service, folder_id)}:")
            for file in files:
                file_type = get_file_type_emoji(file.get('mimeType'))
                file_size = file.get('size', 'N/A')
                if file_size != 'N/A':
                    file_size = format_file_size(int(file_size))
                logger.info(f"{indent}  {file_type} {file.get('name')} ({file_size}) (ID: {file.get('id')})")
    
    except Exception as e:
        logger.error(f"Error listing contents of folder {folder_id}: {str(e)}")

def get_item_name(service, item_id):
    """Get the name of an item by its ID"""
    try:
        if item_id == 'root':
            return 'My Drive (Root)'
            
        result = service.files().get(
            fileId=item_id,
            fields="name"
        ).execute()
        
        return result.get('name', f"Unknown ({item_id})")
    except Exception as e:
        logger.error(f"Error getting name for item {item_id}: {str(e)}")
        return f"Error ({item_id})"

def get_file_type_emoji(mime_type):
    """Return an emoji representing file type"""
    if 'image/' in mime_type:
        return '🖼️'
    elif 'video/' in mime_type:
        return '🎬'
    elif 'audio/' in mime_type:
        return '🔊'
    elif 'text/' in mime_type:
        return '📄'
    elif 'application/pdf' in mime_type:
        return '📑'
    elif 'spreadsheet' in mime_type:
        return '📊'
    elif 'document' in mime_type:
        return '📝'
    elif 'presentation' in mime_type:
        return '📽️'
    else:
        return '📁'

def format_file_size(size_bytes):
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"

def find_videos(service, folder_id='root', max_depth=10):
    """Find all video files in Drive and their locations"""
    logger.info("Searching for video files across Google Drive...")
    
    try:
        # Search directly for video files
        results = service.files().list(
            q="mimeType contains 'video/' and trashed=false",
            fields="files(id, name, mimeType, size, parents)"
        ).execute()
        
        videos = results.get('files', [])
        
        if not videos:
            logger.info("No video files found in Google Drive.")
            return
        
        logger.info(f"Found {len(videos)} video files:")
        
        for video in videos:
            video_id = video.get('id')
            video_name = video.get('name')
            video_size = format_file_size(int(video.get('size', '0')))
            
            # Get the parent folder
            parent_id = video.get('parents', ['unknown'])[0]
            parent_name = get_item_name(service, parent_id)
            
            # Get full path
            path = get_file_path(service, parent_id)
            
            logger.info(f"🎬 {video_name} ({video_size})")
            logger.info(f"   ID: {video_id}")
            logger.info(f"   Location: {path}")
            logger.info(f"   Parent Folder: {parent_name} (ID: {parent_id})")
            
            # Check if this folder has the expected companion files
            companion_files = check_companion_files(service, parent_id)
            logger.info(f"   Companion Files: {', '.join(companion_files) if companion_files else 'None'}")
            logger.info("-" * 80)
            
    except Exception as e:
        logger.error(f"Error searching for videos: {str(e)}")

def get_file_path(service, folder_id, path=None):
    """Get the full path to a file or folder"""
    if path is None:
        path = []
    
    if folder_id == 'root':
        path.insert(0, 'My Drive')
        return ' > '.join(path)
    
    try:
        folder = service.files().get(
            fileId=folder_id,
            fields='name,parents'
        ).execute()
        
        folder_name = folder.get('name', 'Unknown')
        path.insert(0, folder_name)
        
        # Get parent folders recursively
        parents = folder.get('parents', [])
        if parents:
            return get_file_path(service, parents[0], path)
        else:
            return ' > '.join(path)
    except Exception as e:
        logger.error(f"Error getting path for {folder_id}: {str(e)}")
        return ' > '.join(path) if path else 'Unknown path'

def check_companion_files(service, folder_id):
    """Check if a folder has the expected companion files for video upload"""
    expected_files = ['title.txt', 'description.txt', 'tags.txt', 'thumbnail.jpg']
    found_files = []
    
    try:
        results = service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name)"
        ).execute()
        
        files = results.get('files', [])
        filenames = [file.get('name', '') for file in files]
        
        for expected in expected_files:
            if expected in filenames:
                found_files.append(expected)
                
        return found_files
    except Exception as e:
        logger.error(f"Error checking companion files in folder {folder_id}: {str(e)}")
        return []

def evaluate_upload_readiness(service):
    """Evaluate which videos are ready for upload based on companion files"""
    logger.info("Evaluating which videos are ready for upload...")
    
    try:
        # Search for video files
        results = service.files().list(
            q="mimeType contains 'video/' and trashed=false",
            fields="files(id, name, parents)"
        ).execute()
        
        videos = results.get('files', [])
        
        if not videos:
            logger.info("No videos found to evaluate.")
            return
        
        ready_videos = []
        incomplete_videos = []
        
        for video in videos:
            video_name = video.get('name')
            parent_id = video.get('parents', ['unknown'])[0]
            parent_name = get_item_name(service, parent_id)
            
            companion_files = check_companion_files(service, parent_id)
            missing_files = [f for f in ['title.txt', 'description.txt', 'tags.txt', 'thumbnail.jpg'] if f not in companion_files]
            
            if not missing_files:
                ready_videos.append((video_name, parent_name, parent_id))
            else:
                incomplete_videos.append((video_name, parent_name, parent_id, missing_files))
        
        logger.info(f"Videos ready for upload ({len(ready_videos)}):")
        for video_name, parent_name, parent_id in ready_videos:
            logger.info(f"✅ {video_name} in folder {parent_name} (ID: {parent_id})")
        
        logger.info(f"\nVideos missing companion files ({len(incomplete_videos)}):")
        for video_name, parent_name, parent_id, missing_files in incomplete_videos:
            logger.info(f"❌ {video_name} in folder {parent_name} (ID: {parent_id})")
            logger.info(f"   Missing: {', '.join(missing_files)}")
        
    except Exception as e:
        logger.error(f"Error evaluating upload readiness: {str(e)}")

def find_folder_by_name(service, folder_name, parent_id='root'):
    """Search for a folder by name recursively"""
    logger.info(f"Searching for folder named '{folder_name}'...")
    
    try:
        # Direct search first
        results = service.files().list(
            q=f"name contains '{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name, parents)"
        ).execute()
        
        folders = results.get('files', [])
        
        if folders:
            logger.info(f"Found {len(folders)} folders matching '{folder_name}':")
            for folder in folders:
                folder_id = folder.get('id')
                exact_name = folder.get('name')
                path = get_file_path(service, folder_id)
                logger.info(f"📁 {exact_name} (ID: {folder_id})")
                logger.info(f"   Path: {path}")
                
                # Check contents
                has_videos = check_folder_for_videos(service, folder_id)
                if has_videos:
                    logger.info(f"   ✅ This folder contains videos")
                else:
                    subfolders_with_videos = find_subfolders_with_videos(service, folder_id)
                    if subfolders_with_videos:
                        logger.info(f"   ✅ This folder has {len(subfolders_with_videos)} subfolders containing videos:")
                        for subfolder_name, subfolder_id in subfolders_with_videos:
                            logger.info(f"      📁 {subfolder_name} (ID: {subfolder_id})")
                    else:
                        logger.info(f"   ❌ No videos found in this folder or its subfolders")
        else:
            logger.info(f"No folders found matching '{folder_name}'")
        
    except Exception as e:
        logger.error(f"Error searching for folder '{folder_name}': {str(e)}")

def check_folder_for_videos(service, folder_id):
    """Check if a folder contains video files"""
    try:
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType contains 'video/' and trashed=false",
            fields="files(id, name)"
        ).execute()
        
        videos = results.get('files', [])
        return len(videos) > 0
    except Exception as e:
        logger.error(f"Error checking folder {folder_id} for videos: {str(e)}")
        return False

def find_subfolders_with_videos(service, folder_id):
    """Find subfolders that contain videos"""
    subfolders_with_videos = []
    
    try:
        # Get subfolders
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name)"
        ).execute()
        
        subfolders = results.get('files', [])
        
        for subfolder in subfolders:
            subfolder_id = subfolder.get('id')
            subfolder_name = subfolder.get('name')
            
            if check_folder_for_videos(service, subfolder_id):
                subfolders_with_videos.append((subfolder_name, subfolder_id))
        
        return subfolders_with_videos
    except Exception as e:
        logger.error(f"Error finding subfolders with videos: {str(e)}")
        return []

def suggest_target_folder(service):
    """Analyze Drive structure and suggest the best folder to target for uploads"""
    logger.info("Analyzing Drive structure to suggest the best folder to target...")
    
    try:
        # Find all folders with videos
        folder_scores = {}
        
        # Get top-level folders
        results = service.files().list(
            q="'root' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name)"
        ).execute()
        
        folders = results.get('files', [])
        
        for folder in folders:
            folder_id = folder.get('id')
            folder_name = folder.get('name')
            
            # Check if this folder directly contains videos
            direct_videos = count_videos_in_folder(service, folder_id)
            
            # Check subfolders
            subfolder_results = service.files().list(
                q=f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
                fields="files(id, name)"
            ).execute()
            
            subfolders = subfolder_results.get('files', [])
            
            # If folder has multiple subfolders with videos, it's likely a collection folder
            subfolder_video_counts = []
            total_subfolders_with_videos = 0
            total_videos_in_subfolders = 0
            
            for subfolder in subfolders:
                subfolder_id = subfolder.get('id')
                video_count = count_videos_in_folder(service, subfolder_id)
                
                if video_count > 0:
                    total_subfolders_with_videos += 1
                    total_videos_in_subfolders += video_count
                    subfolder_video_counts.append((subfolder.get('name'), video_count))
            
            # Calculate a score - higher is better
            score = 0
            
            # If the folder itself has videos
            if direct_videos > 0:
                score += direct_videos * 5
            
            # If many subfolders have videos, it's likely our target folder
            if total_subfolders_with_videos > 1:
                score += total_subfolders_with_videos * 20
                score += total_videos_in_subfolders * 2
            
            # If "story" is in the name of many subfolders, it's more likely
            story_subfolders = len([sf for sf, _ in subfolder_video_counts if 'story' in sf.lower()])
            if story_subfolders > 0:
                score += story_subfolders * 30
            
            # If the folder name contains relevant keywords
            relevant_keywords = ['story', 'stories', 'video', 'upload', 'gemini', 'content']
            for keyword in relevant_keywords:
                if keyword.lower() in folder_name.lower():
                    score += 50
            
            # Store score
            folder_scores[folder_id] = {
                'name': folder_name,
                'score': score,
                'direct_videos': direct_videos,
                'subfolders_with_videos': total_subfolders_with_videos,
                'total_videos': direct_videos + total_videos_in_subfolders,
                'video_subfolders': subfolder_video_counts
            }
        
        # Find the folder with the highest score
        suggested_folders = sorted([(fid, data) for fid, data in folder_scores.items() if data['score'] > 0], 
                                key=lambda x: x[1]['score'], reverse=True)
        
        logger.info("Folder analysis results:")
        
        if not suggested_folders:
            logger.info("No suitable folders found with videos.")
            return
        
        for folder_id, data in suggested_folders:
            logger.info(f"📁 {data['name']} (ID: {folder_id})")
            logger.info(f"   Score: {data['score']}")
            logger.info(f"   Direct Videos: {data['direct_videos']}")
            logger.info(f"   Subfolders with Videos: {data['subfolders_with_videos']}")
            logger.info(f"   Total Videos: {data['total_videos']}")
            
            if data['video_subfolders']:
                logger.info("   Video-containing subfolders:")
                for subfolder_name, count in data['video_subfolders']:
                    logger.info(f"      📁 {subfolder_name}: {count} videos")
            
            logger.info("-" * 80)
        
        top_suggestion = suggested_folders[0][1]['name'] if suggested_folders else None
        top_id = suggested_folders[0][0] if suggested_folders else None
        
        if top_suggestion:
            logger.info(f"✅ Recommended target folder: {top_suggestion} (ID: {top_id})")
            logger.info(f"Update your script with: python main.py --folder \"{top_suggestion}\"")
            
    except Exception as e:
        logger.error(f"Error suggesting target folder: {str(e)}")

def count_videos_in_folder(service, folder_id):
    """Count the number of video files in a folder"""
    try:
        results = service.files().list(
            q=f"'{folder_id}' in parents and mimeType contains 'video/' and trashed=false",
            fields="files(id)"
        ).execute()
        
        return len(results.get('files', []))
    except Exception as e:
        logger.error(f"Error counting videos in folder {folder_id}: {str(e)}")
        return 0

def main():
    """Main execution function"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Google Drive Explorer')
    parser.add_argument('--list-all', action='store_true', help='List all folders and files')
    parser.add_argument('--find-videos', action='store_true', help='Find all video files')
    parser.add_argument('--find-folder', type=str, help='Search for a specific folder by name')
    parser.add_argument('--evaluate', action='store_true', help='Evaluate videos ready for upload')
    parser.add_argument('--suggest', action='store_true', help='Suggest the best folder to target')
    parser.add_argument('--max-depth', type=int, default=3, help='Maximum depth for folder traversal')
    args = parser.parse_args()
    
    try:
        # Initialize Google Drive service
        service = build_drive_service()
        
        # By default, suggest the target folder if no action is specified
        if not (args.list_all or args.find_videos or args.find_folder or args.evaluate or args.suggest):
            args.suggest = True
        
        if args.list_all:
            logger.info("=== Listing all folders and files in Google Drive ===")
            get_folder_contents(service, 'root', 0, args.max_depth)
        
        if args.find_videos:
            logger.info("\n=== Finding all video files in Google Drive ===")
            find_videos(service)
        
        if args.find_folder:
            logger.info(f"\n=== Searching for folder '{args.find_folder}' ===")
            find_folder_by_name(service, args.find_folder)
        
        if args.evaluate:
            logger.info("\n=== Evaluating videos ready for upload ===")
            evaluate_upload_readiness(service)
        
        if args.suggest:
            logger.info("\n=== Suggesting target folder for video uploads ===")
            suggest_target_folder(service)
        
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")

if __name__ == "__main__":
    logger.info("Starting Google Drive Explorer")
    main()
    logger.info("Google Drive Explorer completed")
