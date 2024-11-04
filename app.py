import os
import re
from datetime import datetime
from typing import List, Optional, Tuple
import json
import logging
from urllib.parse import urlparse, parse_qs

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.formatters import TextFormatter
from tqdm import tqdm

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class YouTubeTranscriptDownloader:
    def __init__(self, output_dir: str = "transcripts"):
        """Initialize the downloader with an output directory."""
        self.output_dir = output_dir
        self.formatter = TextFormatter()
        
    def _extract_channel_id(self, channel_url: str) -> str:
        """Extract channel ID from various YouTube channel URL formats."""
        parsed_url = urlparse(channel_url)
        
        if 'youtube.com' not in parsed_url.netloc:
            raise ValueError("Not a valid YouTube URL")
            
        path = parsed_url.path
        
        # Handle different URL formats
        if '/channel/' in path:
            return path.split('/channel/')[1].split('/')[0]
        elif '/c/' in path or '/user/' in path:
            # Need to make an additional request to get the channel ID
            return self._get_channel_id_from_custom_url(channel_url)
        elif '@' in path:
            return path.split('@')[1].split('/')[0]
        else:
            raise ValueError("Could not extract channel ID from URL")

    def _get_channel_id_from_custom_url(self, url: str) -> str:
        """Get channel ID from custom URL using yt-dlp."""
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(url, download=False)
            return result.get('channel_id')

    def _create_output_dirs(self, channel_name: str) -> Tuple[str, str]:
        """Create necessary output directories."""
        clean_channel_name = re.sub(r'[<>:"/\\|?*]', '', channel_name)
        channel_dir = os.path.join(self.output_dir, clean_channel_name)
        transcript_dir = os.path.join(channel_dir, "transcripts")
        
        os.makedirs(channel_dir, exist_ok=True)
        os.makedirs(transcript_dir, exist_ok=True)
        
        return channel_dir, transcript_dir

    def _get_channel_videos(self, channel_url: str) -> Tuple[str, List[dict]]:
        """Extract channel name and video information using yt-dlp."""
        ydl_opts = {
            'ignoreerrors': True,
            'extract_flat': True,
            'quiet': True,
            'no_warnings': True,
            'playlistend': 50,  # Limit for testing, remove or adjust as needed
            'extract_flat': True,
            'playlist_items': '1:50',  # Adjust range as needed
            'skip_download': True,
            'format': 'best'
        }
        
        try:
            # First, get the channel's uploads playlist
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"Fetching channel info from: {channel_url}")
                channel_info = ydl.extract_info(channel_url, download=False)
                
                if not channel_info:
                    raise Exception("Could not fetch channel information")
                
                channel_name = channel_info.get('channel', 'Unknown_Channel')
                channel_id = channel_info.get('channel_id')
                
                if not channel_id:
                    raise Exception("Could not find channel ID")
                
                # Get the channel's uploads playlist
                playlist_url = f'https://www.youtube.com/channel/{channel_id}/videos'
                playlist_info = ydl.extract_info(playlist_url, download=False)
                
                if not playlist_info or 'entries' not in playlist_info:
                    raise Exception("Could not fetch channel videos")
                
                # Filter out None entries and extract required information
                videos = []
                for entry in playlist_info['entries']:
                    if entry and isinstance(entry, dict):
                        video_id = entry.get('id')
                        if video_id and entry.get('title'):
                            videos.append({
                                'id': video_id,
                                'title': entry['title'],
                                'upload_date': entry.get('upload_date', 'Unknown_Date')
                            })
                
                logger.info(f"Found {len(videos)} videos in channel: {channel_name}")
                return channel_name, videos
                
        except Exception as e:
            logger.error(f"Error fetching channel videos: {str(e)}")
            raise

    def _get_transcript(self, video_id: str, video_title: str) -> Optional[str]:
        """Attempt to get transcript using YouTube's API."""
        try:
            logger.info(f"Fetching transcript for video: {video_title} ({video_id})")
            transcript = YouTubeTranscriptApi.get_transcript(video_id)
            
            # Format transcript with timestamps
            formatted_transcript = []
            for entry in transcript:
                timestamp = int(entry['start'])
                minutes = timestamp // 60
                seconds = timestamp % 60
                text = entry['text'].strip()
                formatted_transcript.append(f"[{minutes:02d}:{seconds:02d}] {text}")
            
            return "\n".join(formatted_transcript)
            
        except Exception as e:
            logger.warning(f"Could not get transcript for {video_id}: {str(e)}")
            return None

    def _use_whisper(self, video_url: str) -> Optional[str]:
        """Use Whisper to generate transcript."""
        try:
            # Download audio using yt-dlp
            ydl_opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
                'quiet': True,
                'no_warnings': True,
                'outtmpl': 'temp_audio'
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            # TODO: Add your Whisper implementation here
            # audio_path = 'temp_audio.mp3'
            # transcript = your_whisper_function(audio_path)
            
            # Clean up
            if os.path.exists('temp_audio.mp3'):
                os.remove('temp_audio.mp3')
            
            return None  # Replace with actual transcript when Whisper is implemented
            
        except Exception as e:
            logger.error(f"Whisper transcription failed: {str(e)}")
            return None

    def download_channel_transcripts(self, channel_url: str) -> None:
        """Download transcripts for all videos in a channel."""
        try:
            # Get channel information
            channel_name, videos = self._get_channel_videos(channel_url)
            channel_dir, transcript_dir = self._create_output_dirs(channel_name)
            
            # Create metadata file
            metadata = {
                'channel_url': channel_url,
                'channel_name': channel_name,
                'download_date': datetime.now().isoformat(),
                'videos': []
            }
            
            logger.info(f"Processing {len(videos)} videos from {channel_name}")
            
            # Process each video
            successful_downloads = 0
            for video in tqdm(videos, desc="Downloading transcripts"):
                video_id = video['id']
                video_title = video['title']
                video_url = f"https://www.youtube.com/watch?v={video_id}"
                
                # Try YouTube's built-in transcripts first
                transcript = self._get_transcript(video_id, video_title)
                transcript_source = "youtube_api"
                
                # Fall back to Whisper if needed and implemented
                if transcript is None and self._use_whisper is not None:
                    logger.info(f"Attempting Whisper for {video_title}")
                    transcript = self._use_whisper(video_url)
                    transcript_source = "whisper"
                
                if transcript:
                    # Create a clean filename
                    clean_title = re.sub(r'[<>:"/\\|?*]', '', video_title)
                    filename = f"{video['upload_date']}_{clean_title[:50]}_{video_id}.txt"
                    filepath = os.path.join(transcript_dir, filename)
                    
                    # Save transcript
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(f"Title: {video_title}\n")
                        f.write(f"Video ID: {video_id}\n")
                        f.write(f"Upload Date: {video['upload_date']}\n")
                        f.write(f"Transcript Source: {transcript_source}\n")
                        f.write("\n" + "="*50 + "\n\n")
                        f.write(transcript)
                    
                    successful_downloads += 1
                    
                    # Update metadata
                    metadata['videos'].append({
                        'video_id': video_id,
                        'title': video_title,
                        'upload_date': video['upload_date'],
                        'transcript_source': transcript_source,
                        'transcript_file': filename
                    })
            
            # Save metadata
            metadata_path = os.path.join(channel_dir, 'metadata.json')
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"\nDownload completed. Successfully downloaded {successful_downloads} out of {len(videos)} transcripts.")
            logger.info(f"Transcripts saved to: {transcript_dir}")
            logger.info(f"Metadata saved to: {metadata_path}")
            
        except Exception as e:
            logger.error(f"Error processing channel: {str(e)}")
            raise

def main():
    """Main function to run the transcript downloader."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Download transcripts from a YouTube channel")
    parser.add_argument("--channel-url", help="URL of the YouTube channel")
    parser.add_argument("--output", "-o", default="transcripts",
                      help="Output directory for transcripts (default: transcripts)")
    parser.add_argument("--debug", action="store_true",
                      help="Enable debug logging")
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        # If channel URL not provided in command line, prompt for it
        channel_url = args.channel_url
        if not channel_url:
            print("\nYouTube Channel URL can be in any of these formats:")
            print("- https://www.youtube.com/@ChannelName")
            print("- https://www.youtube.com/c/ChannelName")
            print("- https://www.youtube.com/channel/CHANNEL_ID")
            print("- https://www.youtube.com/user/USERNAME\n")
            channel_url = input("Please enter the YouTube channel URL: ").strip()
        
        if not channel_url:
            print("No channel URL provided. Exiting.")
            exit(1)
            
        # Create downloader and process channel
        downloader = YouTubeTranscriptDownloader(output_dir=args.output)
        downloader.download_channel_transcripts(channel_url)
        
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
        exit(0)
    except Exception as e:
        logger.error(f"Program failed: {str(e)}")
        exit(1)

if __name__ == "__main__":
    main()