import json
import os
from openrouteservice import convert
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import subprocess

app = Flask(__name__)
CORS(app, origins=["https://e-bike-dun.vercel.app"])

@app.route("/run-navigation", methods=["POST"])
def run_navigation():
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        nav_path = os.path.join(base_dir, "navigation.py")

        tags = request.json.get("tags", [])
        if isinstance(tags, str):
            try:
                tags = json.loads(tags)
            except json.JSONDecodeError:
                return jsonify({"status": "error", "message": "Invalid JSON format for tags."}), 400

        # Convert tags to the "key=value,key2=value2" format expected by navigation.py
        if tags and isinstance(tags, list) and tags:
            if isinstance(tags[0], dict): # e.g., [{"key": "amenity", "value": "cafe"}]
                tag_str = ",".join(f"{t['key']}={t['value']}" for t in tags)
            elif isinstance(tags[0], str): # e.g., ["amenity=cafe"]
                tag_str = ",".join(tags)
            else:
                return jsonify({"status": "error", "message": "Unsupported tag list format."}), 400
        else:
            # Handle cases where tags list is empty or not a list
            tag_str = ""
            print("No tags provided or tags format is unexpected, navigation.py will likely exit.")


        print(f"Received tags: {tags}")
        print(f"Constructed tag string for navigation.py: {tag_str}")

        # Execute navigation.py as a subprocess
        # `--tags` argument is passed with the constructed string
        # `check=True` will raise a CalledProcessError if navigation.py returns a non-zero exit code
        result = subprocess.run(
            ["python", nav_path, "--tags", tag_str],
            capture_output=True, # Capture stdout and stderr for debugging
            text=True,           # Decode stdout/stderr as text
            check=True
        )
        print("navigation.py stdout:\n", result.stdout)
        print("navigation.py stderr:\n", result.stderr)

        # If subprocess.run did not raise an exception, it means navigation.py ran successfully
        return jsonify({"status": "success"})

    except subprocess.CalledProcessError as e:
        # This block catches errors specifically from navigation.py failing
        print(f"Navigation script failed with exit code {e.returncode}. Stderr:\n{e.stderr}")
        return jsonify({
            "status": "error",
            "message": "Navigation generation failed. " + e.stderr.strip()
        }), 500
    except json.JSONDecodeError:
        return jsonify({"status": "error", "message": "Invalid JSON in request body."}), 400
    except Exception as e:
        # Catch any other unexpected errors during the process
        print(f"An unexpected error occurred in /run-navigation: {e}")
        return jsonify({"status": "error", "message": f"Server error: {str(e)}"}), 500

# --- Endpoint to serve the generated map HTML file ---
@app.route("/get-map", methods=["GET"])
def get_map():
    try:
        # Construct the path to the saved map file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(base_dir, "public", "maps")
        output_path = os.path.join(output_dir, "maizuru_full_tsp_route.html")

        # Check if the map file exists before sending it
        if os.path.exists(output_path):
            print(f"Serving map from: {output_path}")
            return send_file(output_path, mimetype='text/html')
        else:
            print(f"Map file not found at: {output_path}")
            return jsonify({"status": "error", "message": "Map file not found. Please run navigation first."}), 404
    except Exception as e:
        print(f"Error serving map file: {e}")
        return jsonify({"status": "error", "message": f"Server error when fetching map: {str(e)}"}), 500

# --- Health Check Endpoint (Good practice for deployments) ---
@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy"}), 200