from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import os
import re
import sys
import logging
import tempfile

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Set up logging
logging.basicConfig(level=logging.INFO)

# Store video info temporarily
video_info_cache = {}

@app.route('/convert', methods=['POST'])
def convert():
    try:
        youtube_url = request.form.get('url')
        if not youtube_url:
            return jsonify({"success": False, "error": "YouTube URL is required"}), 400
        
        logging.info(f"Received YouTube URL: {youtube_url}")
        
        # Path to the cookies.txt file (exported from your browser)
        cookies_path = "path/to/your/cookies.txt"  # Update with the correct path
        
        # Use yt-dlp to extract the video title with cookies for authentication
        result = subprocess.run(
            ["yt-dlp", "--get-title", "--cookies", cookies_path, youtube_url],
            capture_output=True, text=True, check=True
        )
        video_title = result.stdout.strip()
        logging.info(f"Extracted video title: {video_title}")
        
        # Sanitize the video title
        sanitized_title = re.sub(r'[\\/*?:"<>|]', "", video_title)
        
        # Store the URL and title mapping for later use
        video_info_cache[sanitized_title] = {
            'url': youtube_url,
            'title': sanitized_title
        }
        
        # Return the sanitized title as an identifier
        download_url = f"http://127.0.0.1:5000/download/{sanitized_title}"
        return jsonify({"success": True, "mp3Link": download_url})
    
    except subprocess.CalledProcessError as e:
        logging.error(f"Subprocess error: {e.stderr}")
        return jsonify({"success": False, "error": f"yt-dlp error: {e.stderr}"}), 500
    except Exception as e:
        logging.error(f"General error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    try:
        if filename not in video_info_cache:
            return jsonify({"success": False, "error": "Video information not found"}), 404
        
        video_info = video_info_cache[filename]
        youtube_url = video_info['url']
        
        # Create a temporary directory for the download
        with tempfile.TemporaryDirectory() as temp_dir:
            output_file = os.path.join(temp_dir, f"{filename}.mp3")
            
            # Download and convert the file only when requested
            subprocess.run(
                ["yt-dlp", "-x", "--audio-format", "mp3", "-o", output_file, youtube_url],
                check=True
            )
            
            logging.info(f"Audio downloaded successfully to temporary location: {output_file}")
            
            # Send the file directly from the temporary directory
            return send_file(
                output_file,
                as_attachment=True,
                download_name=f"{filename}.mp3"
            )
            
    except subprocess.CalledProcessError as e:
        logging.error(f"Error in downloading file: {e.stderr}")
        return jsonify({"success": False, "error": f"Download error: {e.stderr}"}), 500
    except Exception as e:
        logging.error(f"Error in downloading file: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        # Clean up the video info from cache
        if filename in video_info_cache:
            del video_info_cache[filename]

if __name__ == '__main__':
    app.run(debug=True)