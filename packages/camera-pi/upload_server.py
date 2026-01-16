#!/usr/bin/env python3
"""
Simple HTTP upload server for receiving images from Raspberry Pi camera.
Run this on your Windows laptop in PowerShell.
"""

from flask import Flask, request, jsonify
from pathlib import Path
import logging

app = Flask(__name__)

# Configure upload directory
UPLOAD_DIR = Path.home() / "Downloads"
UPLOAD_DIR.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.route('/upload', methods=['POST'])
def upload_file():
    """Receive uploaded image file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    # Save file to Downloads
    filepath = UPLOAD_DIR / file.filename
    file.save(str(filepath))

    logger.info(f"✓ Received: {file.filename} -> {filepath}")

    return jsonify({
        'success': True,
        'filename': file.filename,
        'path': str(filepath)
    })


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'ok', 'upload_dir': str(UPLOAD_DIR)})


if __name__ == '__main__':
    print("=" * 60)
    print("Birthmark Image Upload Server")
    print("=" * 60)
    print(f"Upload directory: {UPLOAD_DIR}")
    print(f"Server running on: http://0.0.0.0:8888")
    print("Ready to receive images from Raspberry Pi")
    print("=" * 60)
    print()

    app.run(host='0.0.0.0', port=8888, debug=False)
