import os
import sys
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.request import urlretrieve

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

PORT = 8554
DEFAULT_VIDEO_NAME = "sample_crowd.mp4"
VIDEO_PATH = os.path.join(BACKEND_DIR, DEFAULT_VIDEO_NAME)
DOWNLOAD_URL = "https://raw.githubusercontent.com/intel-iot-devkit/sample-videos/master/people-detection.mp4"

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

# Global frame buffer for streamer
class FrameServer:
    def __init__(self):
        self.lock = threading.Lock()
        self.current_frame = None
        self.running = False
        self.video_source = VIDEO_PATH

    def start_capture(self):
        self.running = True
        threading.Thread(target=self._capture_loop, daemon=True).start()

    def _capture_loop(self):
        import cv2
        
        while self.running:
            # Check if source is a YouTube link
            source = self.video_source
            is_youtube = "youtube.com" in source.lower() or "youtu.be" in source.lower()
            
            if is_youtube:
                # Extract fresh URL on each loop start in case the previous lease expired
                actual_source = get_youtube_stream(source)
                if not actual_source:
                    print(f"{Colors.FAIL}[ERROR] YouTube link extraction failed. Retrying in 5s...{Colors.ENDC}")
                    time.sleep(5)
                    continue
            else:
                actual_source = source

            print(f"{Colors.BLUE}[INFO] Opening video source: {source}{Colors.ENDC}")
            cap = cv2.VideoCapture(actual_source)
            if not cap.isOpened():
                print(f"{Colors.FAIL}[ERROR] Could not open video source. Retrying in 5s...{Colors.ENDC}")
                time.sleep(5)
                continue

            fps = cap.get(cv2.CAP_PROP_FPS) or 25
            frame_delay = 1.0 / fps

            while self.running:
                start_time = time.time()
                ret, frame = cap.read()
                if not ret:
                    # Video ended, break loop to automatically restart (infinite loop)
                    print(f"{Colors.BLUE}[INFO] Source ended or lease expired. Re-opening...{Colors.ENDC}")
                    break

                # Encode frame as JPEG
                ret_enc, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                if ret_enc:
                    with self.lock:
                        self.current_frame = jpeg.tobytes()

                # Control FPS to match real-time playback
                elapsed = time.time() - start_time
                sleep_time = max(0.001, frame_delay - elapsed)
                time.sleep(sleep_time)

            cap.release()

frame_server = FrameServer()

class StreamingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/video':
            self.send_response(200)
            self.send_header('Age', '0')
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            
            print(f"{Colors.GREEN}[CONNECT] New client connected to live feed from {self.client_address[0]}{Colors.ENDC}")
            try:
                last_frame = None
                while True:
                    with frame_server.lock:
                        frame = frame_server.current_frame
                    
                    if frame and frame != last_frame:
                        self.wfile.write(b'--frame\r\n')
                        self.send_header('Content-Type', 'image/jpeg')
                        self.send_header('Content-Length', str(len(frame)))
                        self.end_headers()
                        self.wfile.write(frame)
                        self.wfile.write(b'\r\n')
                        last_frame = frame
                    else:
                        time.sleep(0.01)
            except Exception as e:
                print(f"{Colors.WARNING}[DISCONNECT] Client disconnected: {self.client_address[0]} ({e}){Colors.ENDC}")
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')

def download_sample_video():
    if os.path.exists(VIDEO_PATH):
        return
        
    print(f"{Colors.BLUE}[INFO] Downloading a high-quality crowd tracking sample video...{Colors.ENDC}")
    print("Please wait a moment...")
    try:
        urlretrieve(DOWNLOAD_URL, VIDEO_PATH)
        print(f"{Colors.GREEN}[SUCCESS] Download complete! Saved to {VIDEO_PATH}{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}[ERROR] Failed to download sample video: {e}{Colors.ENDC}")
        print("Please place your own video file named 'sample_crowd.mp4' in the backend directory.")

def main():
    print(f"{Colors.HEADER}{Colors.BOLD}==================================================")
    print("    Camus Mobility & Occupancy Analytics System    ")
    print("         Live Camera Stream Simulator             ")
    print(f"=================================================={Colors.ENDC}\n")

    # Allow custom video file or YouTube URL via arguments
    if len(sys.argv) > 1:
        custom_path = sys.argv[1]
        is_youtube = "youtube.com" in custom_path.lower() or "youtu.be" in custom_path.lower()
        
        if is_youtube or os.path.exists(custom_path):
            frame_server.video_source = custom_path
            print(f"{Colors.GREEN}[CONFIG] Active video source: {custom_path}{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}[ERROR] Video source not found: {custom_path}{Colors.ENDC}")
            sys.exit(1)
    else:
        # Download sample video if not present
        download_sample_video()

    try:
        import cv2
    except ImportError:
        print(f"{Colors.FAIL}[ERROR] 'opencv-python' is not installed in this environment.{Colors.ENDC}")
        print("Please activate your virtual environment: .\\venv\\Scripts\\activate")
        sys.exit(1)

    # Start capture thread
    frame_server.start_capture()

    # Start HTTP Streaming Server
    server = HTTPServer(('0.0.0.0', PORT), StreamingHandler)
    print("\n" + "=" * 50)
    print(f"{Colors.GREEN}{Colors.BOLD}🎉 Live Stream Simulator Active!{Colors.ENDC}")
    print("=" * 50)
    print(f"Streaming URL: {Colors.BLUE}http://localhost:{PORT}/video{Colors.ENDC}")
    print(f"Video Source:  {frame_server.video_source}")
    print("=" * 50)
    print(f"\n{Colors.BOLD}🚀 HOW TO TEST:{Colors.ENDC}")
    print(f"1. Open VLC Media Player.")
    print(f"2. Press {Colors.BLUE}Ctrl + N{Colors.ENDC} and paste the streaming URL above.")
    print(f"3. In your register_camera.py script, register this stream using:")
    print(f"   {Colors.BLUE}http://localhost:{PORT}/video{Colors.ENDC} as the stream link.")
    print("=" * 50)
    print("\nPress Ctrl+C to stop the simulator server.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping stream simulator...")
        frame_server.running = False
        server.server_close()
        print("Stream simulator stopped.")

if __name__ == '__main__':
    main()
