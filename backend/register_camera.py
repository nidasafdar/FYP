import os
import sys
import time
from urllib.parse import urlparse

# Ensure backend directory is in the path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.append(BACKEND_DIR)

# ANSI Colors for premium terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    print(f"{Colors.HEADER}{Colors.BOLD}==================================================")
    print("    Camus Mobility & Occupancy Analytics System    ")
    print("        Camera Auto-Registration Script           ")
    print(f"=================================================={Colors.ENDC}\n")

def get_youtube_stream(url: str) -> str:
    """Extract direct raw video stream URL from a YouTube watch link."""
    print(f"{Colors.BLUE}[INFO] YouTube URL detected! Extracting direct raw video link...{Colors.ENDC}")
    try:
        import yt_dlp
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'quiet': True,
            'no_warnings': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            stream_url = info.get('url')
            if stream_url:
                print(f"{Colors.GREEN}[SUCCESS] Successfully extracted YouTube raw stream link.{Colors.ENDC}")
                return stream_url
            else:
                print(f"{Colors.FAIL}[ERROR] YouTube extractor did not return a stream URL.{Colors.ENDC}")
                return None
    except ImportError:
        print(f"{Colors.FAIL}[ERROR] 'yt-dlp' library is missing. Install it using: pip install yt-dlp{Colors.ENDC}")
        return None
    except Exception as e:
        print(f"{Colors.FAIL}[ERROR] Failed to extract YouTube stream: {e}{Colors.ENDC}")
        return None

def test_stream_url(stream_url: str) -> bool:
    """Test if the stream URL can be opened by OpenCV."""
    print(f"\n{Colors.BLUE}[INFO] Testing connection to: {stream_url}...{Colors.ENDC}")
    print("This may take up to 10 seconds. Please wait...")
    
    try:
        import cv2
    except ImportError:
        print(f"{Colors.WARNING}[WARN] 'opencv-python' not found. Skipping live stream validation.{Colors.ENDC}")
        return True
        
    start_time = time.time()
    
    is_youtube = "youtube.com" in stream_url.lower() or "youtu.be" in stream_url.lower()
    if is_youtube:
        actual_url = get_youtube_stream(stream_url)
        if not actual_url:
            print(f"{Colors.FAIL}[ERROR] Connection failed: Unable to extract YouTube raw video link.{Colors.ENDC}")
            return False
    else:
        actual_url = stream_url
    
    # Try using cv2.VideoCapture
    cap = cv2.VideoCapture(actual_url)
    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        if ret:
            elapsed = time.time() - start_time
            print(f"{Colors.GREEN}[SUCCESS] Connection successful! Received frames in {elapsed:.2f} seconds.{Colors.ENDC}")
            return True
        else:
            print(f"{Colors.WARNING}[WARN] Stream opened but failed to read a frame. Check if the feed is active.{Colors.ENDC}")
            return False
    else:
        print(f"{Colors.FAIL}[ERROR] Connection failed: Unable to open stream URL.{Colors.ENDC}")
        print("Please check:")
        print("  1. Is the URL formatted correctly (e.g. rtsp://username:password@ip:port/h264) ?")
        print("  2. Is the camera online and reachable from your computer's network?")
        return False

def register_camera(title: str, description: str, stream_url: str) -> dict:
    """Register the camera in the database (via API if running, or direct Supabase)."""
    # 1. Try to register via the local API
    import requests
    api_url = "http://localhost:8000/api/sources"
    payload = {
        "title": title,
        "description": description,
        "mode": "stream",
        "stream_url": stream_url
    }
    
    print(f"\n{Colors.BLUE}[INFO] Connecting to Camus API...{Colors.ENDC}")
    try:
        response = requests.post(api_url, json=payload, timeout=5)
        if response.status_code in [200, 201]:
            data = response.json()
            source = data.get("source")
            print(f"{Colors.GREEN}[SUCCESS] Successfully registered camera via local API server!{Colors.ENDC}")
            return source
        else:
            print(f"{Colors.WARNING}[WARN] Local API server returned code {response.status_code}: {response.text}{Colors.ENDC}")
    except requests.exceptions.RequestException:
        print(f"{Colors.WARNING}[WARN] Local API server is not running on port 8000.{Colors.ENDC}")
    
    # 2. Fallback: Register directly using SourceRepository
    print(f"{Colors.BLUE}[INFO] Falling back to direct Supabase database insertion...{Colors.ENDC}")
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        from source_repository import SourceRepository
        repo = SourceRepository()
        source = repo.create_source(
            title=title,
            description=description,
            mode="stream",
            stream_url=stream_url
        )
        print(f"{Colors.GREEN}[SUCCESS] Successfully registered camera directly in Supabase database!{Colors.ENDC}")
        return source
    except Exception as e:
        print(f"{Colors.FAIL}[ERROR] Failed to register camera directly in database: {e}{Colors.ENDC}")
        print(f"{Colors.WARNING}Please check that your backend/.env file contains correct SUPABASE_URL and SUPABASE_KEY credentials.{Colors.ENDC}")
        return None

def main():
    print_banner()
    
    # Check if we have .env file
    env_path = os.path.join(BACKEND_DIR, ".env")
    if not os.path.exists(env_path):
        print(f"{Colors.WARNING}[WARN] backend/.env was not found.{Colors.ENDC}")
        print("Please create backend/.env with your Supabase credentials first.")
        sys.exit(1)
        
    title = input("Enter camera title/name (e.g. Front Door Camera): ").strip()
    while not title:
        title = input("Title cannot be empty. Enter camera title: ").strip()
        
    description = input("Enter description (e.g. Driveway monitoring): ").strip()
    
    print("\nEnter stream URL. Examples:")
    print("  - RTSP stream: rtsp://admin:password123@192.168.1.100:554/h264Preview_01_main")
    print("  - HTTP MJPEG stream: http://192.168.1.50/mjpeg.cgi")
    print("  - Test Video File: C:\\path\\to\\video.mp4")
    print("  - YouTube Video: https://youtu.be/ZksWoEAhmTU")
    stream_url = input("Enter stream URL: ").strip()
    while not stream_url:
        stream_url = input("Stream URL cannot be empty. Enter stream URL: ").strip()

    # Validate schema for API compatibility
    parsed = urlparse(stream_url)
    # If it's a local file path or YouTube link, don't worry about URL scheme
    is_local_file = os.path.exists(stream_url)
    is_youtube = "youtube.com" in stream_url.lower() or "youtu.be" in stream_url.lower()
    
    if not is_local_file and not is_youtube and parsed.scheme not in ["http", "https", "rtsp"]:
        print(f"\n{Colors.WARNING}[WARN] Stream URL scheme is not rtsp, http, or https. Local API may reject it if not a valid URL.{Colors.ENDC}")
        confirm = input("Are you sure you want to proceed with this URL? (y/n): ").strip().lower()
        if confirm != 'y':
            print("Aborted.")
            sys.exit(0)

    # Test the stream link
    success = test_stream_url(stream_url)
    if not success:
        confirm = input(f"\n{Colors.WARNING}[WARN] Stream validation failed. Do you still want to register this camera? (y/n): {Colors.ENDC}").strip().lower()
        if confirm != 'y':
            print("Aborted.")
            sys.exit(0)
            
    # Register the camera
    source = register_camera(title, description, stream_url)
    
    if source:
        camera_id = source.get("camera_id")
        print("\n" + "=" * 50)
        print(f"{Colors.GREEN}{Colors.BOLD}[SUCCESS] Camera Registered Successfully!{Colors.ENDC}")
        print("=" * 50)
        print(f"Title:       {source.get('title')}")
        print(f"Camera ID:   {Colors.BLUE}{camera_id}{Colors.ENDC}")
        print(f"Stream URL:  {source.get('stream_url') or source.get('streamUrl')}")
        print("=" * 50)
        print(f"\n{Colors.BOLD}🚀 WHAT TO DO NEXT:{Colors.ENDC}")
        print(f"1. Make sure your backend server is running:")
        print(f"   {Colors.BLUE}uvicorn backend.api:app --reload --port 8000{Colors.ENDC}")
        print(f"2. The stream supervisor will automatically detect {Colors.BLUE}{camera_id}{Colors.ENDC} and launch a background detection worker.")
        print(f"3. Open your React frontend dashboard at: {Colors.BLUE}http://localhost:5174{Colors.ENDC}")
        print(f"4. Select '{source.get('title')}' in the source list to see live crowd metrics!")
        print("=" * 50)
    else:
        print(f"\n{Colors.FAIL}[ERROR] Camera registration failed. Please review your setup and try again.{Colors.ENDC}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
        sys.exit(0)
