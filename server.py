from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import os
import re
import logging
import tempfile
from functools import wraps
import time
from werkzeug.utils import secure_filename

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure yt-dlp options
YT_DLP_OPTIONS = [
    '--no-check-certificates',
    '--no-warnings',
    '--extract-audio',
    '--audio-format', 'mp3',
    '--audio-quality', '0',
    '--prefer-ffmpeg',
    '--no-playlist',
    '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
    '--add-header', 'Accept-Language:en-US,en;q=0.9',
    '--geo-bypass'
]

# Store video info temporarily
video_info_cache = {}

def validate_youtube_url(url):
    youtube_regex = r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$'
    if not re.match(youtube_regex, url):
        raise ValueError("Invalid YouTube URL format")
    return url

@app.route('/')
def health_check():
    return jsonify({"status": "healthy", "message": "YouTube to MP3 converter is running"}), 200

@app.route('/convert', methods=['POST'])
def convert():
    try:
        youtube_url = request.form.get('url')
        if not youtube_url:
            return jsonify({"success": False, "error": "YouTube URL is required"}), 400

        try:
            youtube_url = validate_youtube_url(youtube_url)
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 400

        logger.info(f"Processing YouTube URL: {youtube_url}")

        # First try to get just the title
        try:
            result = subprocess.run(
                ["yt-dlp", "--get-title", "--no-warnings"] + YT_DLP_OPTIONS + [youtube_url],
                capture_output=True,
                text=True,
                check=True
            )
            video_title = result.stdout.strip()
        except subprocess.CalledProcessError as e:
            if "Sign in to confirm you're not a bot" in e.stderr:
                return jsonify({
                    "success": False,
                    "error": "YouTube bot detection triggered. Please try again later."
                }), 429
            elif "Video unavailable" in e.stderr:
                return jsonify({
                    "success": False,
                    "error": "This video is unavailable or private."
                }), 400
            else:
                logger.error(f"Error getting video title: {e.stderr}")
                return jsonify({
                    "success": False,
                    "error": "Unable to process this video. Please try another."
                }), 500

        # Generate a unique identifier for the video
        sanitized_title = secure_filename(video_title)
        
        # Store the URL and title mapping for later use
        video_info_cache[sanitized_title] = {
            'url': youtube_url,
            'title': video_title
        }

        # Return the download link
        download_url = f"/download/{sanitized_title}"
        return jsonify({
            "success": True,
            "mp3Link": download_url,
            "title": video_title
        })

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred. Please try again."
        }), 500

@app.route('/download/<filename>')
def download_file(filename):
    try:
        if filename not in video_info_cache:
            return jsonify({
                "success": False,
                "error": "Download link expired or invalid"
            }), 404

        video_info = video_info_cache[filename]
        youtube_url = video_info['url']

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, f"{filename}.mp3")
            
            try:
                # Download and convert the file
                subprocess.run(
                    ["yt-dlp"] + YT_DLP_OPTIONS + ["-o", output_file, youtube_url],
                    check=True,
                    capture_output=True,
                    text=True
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Error in downloading file: {e.stderr}")
                if "Sign in to confirm you're not a bot" in e.stderr:
                    return jsonify({
                        "success": False,
                        "error": "YouTube bot detection triggered. Please try again later."
                    }), 429
                return jsonify({
                    "success": False,
                    "error": "Failed to download the video. Please try again."
                }), 500

            logger.info(f"Successfully processed: {filename}")
            
            return send_file(
                output_file,
                as_attachment=True,
                download_name=f"{filename}.mp3"
            )

    except Exception as e:
        logger.error(f"Error in downloading file: {str(e)}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred during download"
        }), 500
    finally:
        # Clean up the video info from cache
        if filename in video_info_cache:
            del video_info_cache[filename]

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)