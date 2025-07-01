from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess
import os
import json

app = Flask(__name__)
CORS(app, origins=["https://e-bike-dun.vercel.app"]) # Ensure this matches your frontend's deployed URL if different from the example

@app.route("/run-navigation", methods=["POST"])
def run_navigation():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        nav_path = os.path.join(base_dir, "navigation.py")

        tags = request.json.get("tags", [])
        if isinstance(tags, str):
            tags = json.loads(tags)

        if tags and isinstance(tags[0], dict):
            tag_str = ",".join(f"{t['key']}={t['value']}" for t in tags)
        else:
            tag_str = ",".join(tags)

        print("Received tags:", tags)
        print("Constructed tag string:", tag_str)

        subprocess.run(["python", nav_path, "--tags", tag_str], check=True)

        # The map is now generated and saved in public/maps
        return jsonify({"status": "success"})
    except subprocess.CalledProcessError as e:
        print(f"Navigation script failed with error: {e}")
        return jsonify({"status": "error", "message": f"Navigation script error: {e.stderr.decode()}"}), 500
    except Exception as e:
        print("Navigation failed:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# NEW ENDPOINT TO SERVE THE MAP HTML
@app.route("/get-map", methods=["GET"])
def get_map():
    try:
        output_dir = os.path.join(os.path.dirname(__file__), "public", "maps")
        output_path = os.path.join(output_dir, "maizuru_full_tsp_route.html")

        if os.path.exists(output_path):
            return send_file(output_path, mimetype='text/html')
        else:
            return jsonify({"status": "error", "message": "Map file not found. Run navigation first."}), 404
    except Exception as e:
        print("Error serving map:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# Health check (from previous suggestion, good to keep)
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200

# Make sure to use gunicorn for production deployment
# app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000))) # Remove or comment out for gunicorn