from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import os
import re
import logging
import tempfile
from functools import wraps
from werkzeug.utils import secure_filename
import hashlib
import time

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Enhanced logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure rate limiting
RATE_LIMIT = 60  # seconds
rate_limit_dict = {}

def rate_limit(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        ip = request.remote_addr
        current_time = time.time()
        
        if ip in rate_limit_dict:
            time_passed = current_time - rate_limit_dict[ip]
            if time_passed < RATE_LIMIT:
                return jsonify({
                    "success": False,
                    "error": f"Rate limit exceeded. Please wait {int(RATE_LIMIT - time_passed)} seconds"
                }), 429
        
        rate_limit_dict[ip] = current_time
        return f(*args, **kwargs)
    return decorated_function

# Store video info temporarily with TTL
class CacheWithTTL:
    def __init__(self, ttl=3600):  # 1 hour TTL
        self.cache = {}
        self.ttl = ttl

    def set(self, key, value):
        self.cache[key] = {
            'value': value,
            'timestamp': time.time()
        }

    def get(self, key):
        if key not in self.cache:
            return None
        
        item = self.cache[key]
        if time.time() - item['timestamp'] > self.ttl:
            del self.cache[key]
            return None
            
        return item['value']

    def delete(self, key):
        if key in self.cache:
            del self.cache[key]

video_info_cache = CacheWithTTL()

def validate_youtube_url(url):
    youtube_regex = r'^(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+$'
    if not re.match(youtube_regex, url):
        raise ValueError("Invalid YouTube URL format")
    return url

@app.route('/convert', methods=['POST'])
@rate_limit
def convert():
    try:
        youtube_url = request.form.get('url')
        if not youtube_url:
            return jsonify({"success": False, "error": "YouTube URL is required"}), 400

        # Validate YouTube URL
        try:
            youtube_url = validate_youtube_url(youtube_url)
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 400

        logger.info(f"Processing YouTube URL: {youtube_url}")

        # Extract video title
        result = subprocess.run(
            ["yt-dlp", "--get-title", youtube_url],
            capture_output=True,
            text=True,
            check=True
        )
        video_title = result.stdout.strip()
        
        # Generate a unique identifier for the video
        identifier = hashlib.md5(f"{youtube_url}_{time.time()}".encode()).hexdigest()
        
        # Sanitize the video title
        sanitized_title = secure_filename(video_title)
        
        # Store in cache
        video_info_cache.set(identifier, {
            'url': youtube_url,
            'title': sanitized_title
        })

        download_url = f"/download/{identifier}"
        return jsonify({
            "success": True,
            "mp3Link": download_url,
            "title": sanitized_title
        })

    except subprocess.CalledProcessError as e:
        logger.error(f"yt-dlp error: {e.stderr}")
        return jsonify({
            "success": False,
            "error": "Failed to process YouTube video"
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred"
        }), 500

@app.route('/download/<identifier>', methods=['GET'])
@rate_limit
def download_file(identifier):
    try:
        video_info = video_info_cache.get(identifier)
        if not video_info:
            return jsonify({
                "success": False,
                "error": "Download link expired or invalid"
            }), 404

        youtube_url = video_info['url']
        sanitized_title = video_info['title']

        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, f"{sanitized_title}.mp3")
            
            # Download and convert the file
            subprocess.run([
                "yt-dlp",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "-o", output_file,
                youtube_url
            ], check=True)

            logger.info(f"Successfully processed: {sanitized_title}")
            
            return send_file(
                output_file,
                as_attachment=True,
                download_name=f"{sanitized_title}.mp3"
            )

    except subprocess.CalledProcessError as e:
        logger.error(f"Download error: {e.stderr}")
        return jsonify({
            "success": False,
            "error": "Failed to download and convert video"
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred"
        }), 500
    finally:
        video_info_cache.delete(identifier)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)