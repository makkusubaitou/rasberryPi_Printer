#!/usr/bin/env python3
"""
Raspberry Pi Print Server
Receives images via webhook and prints them to a network printer.
"""

import os
import subprocess
import tempfile
import secrets
from functools import wraps
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}


def allowed_file(filename):
    """Check if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def require_api_key(f):
    """Decorator to require API key authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'Missing API key'}), 401
        if not secrets.compare_digest(api_key, Config.API_KEY):
            return jsonify({'error': 'Invalid API key'}), 403
        return f(*args, **kwargs)
    return decorated


def get_printer_name():
    """Get the configured printer name, or discover the default printer."""
    if Config.PRINTER_NAME:
        return Config.PRINTER_NAME
    
    # Try to get the default printer
    try:
        result = subprocess.run(
            ['lpstat', '-d'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and 'system default destination:' in result.stdout:
            return result.stdout.split('system default destination:')[1].strip()
    except Exception:
        pass
    
    return None


def print_image(image_path, copies=1):
    """
    Send an image to the printer using lp command.
    
    Args:
        image_path: Path to the image file
        copies: Number of copies to print
    
    Returns:
        tuple: (success: bool, message: str, job_id: str or None)
    """
    printer = get_printer_name()
    if not printer:
        return False, "No printer configured or found", None
    
    try:
        # Build the lp command
        cmd = [
            'lp',
            '-d', printer,
            '-n', str(copies),
        ]
        
        # Add any extra options from config
        if Config.PRINT_OPTIONS:
            for option in Config.PRINT_OPTIONS:
                cmd.extend(['-o', option])
        
        cmd.append(image_path)
        
        # Execute the print command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            # Extract job ID from output like "request id is PrinterName-123 (1 file(s))"
            job_id = None
            if 'request id is' in result.stdout:
                job_id = result.stdout.split('request id is')[1].split()[0]
            return True, "Print job submitted successfully", job_id
        else:
            return False, f"Print failed: {result.stderr}", None
            
    except subprocess.TimeoutExpired:
        return False, "Print command timed out", None
    except Exception as e:
        return False, f"Print error: {str(e)}", None


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring."""
    printer = get_printer_name()
    return jsonify({
        'status': 'ok',
        'printer': printer,
        'printer_configured': printer is not None
    })


@app.route('/print', methods=['POST'])
@require_api_key
def print_endpoint():
    """
    Receive and print an image.
    
    Expects:
        - Form data with 'image' file
        - Optional 'copies' parameter (default: 1)
    
    Headers:
        - X-API-Key: Your API key
    """
    # Check if image file is present
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    
    file = request.files['image']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({
            'error': f'File type not allowed. Allowed types: {", ".join(ALLOWED_EXTENSIONS)}'
        }), 400
    
    # Get number of copies
    try:
        copies = int(request.form.get('copies', 1))
        copies = max(1, min(copies, Config.MAX_COPIES))  # Clamp between 1 and max
    except ValueError:
        copies = 1
    
    # Save the file temporarily
    filename = secure_filename(file.filename)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1]) as tmp:
        file.save(tmp.name)
        temp_path = tmp.name
    
    try:
        # Send to printer
        success, message, job_id = print_image(temp_path, copies)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'job_id': job_id,
                'copies': copies
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 500
            
    finally:
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except Exception:
            pass


@app.route('/printers', methods=['GET'])
@require_api_key
def list_printers():
    """List available printers."""
    try:
        result = subprocess.run(
            ['lpstat', '-p', '-d'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        printers = []
        default_printer = None
        
        for line in result.stdout.split('\n'):
            if line.startswith('printer '):
                parts = line.split()
                if len(parts) >= 2:
                    printers.append(parts[1])
            elif 'system default destination:' in line:
                default_printer = line.split('system default destination:')[1].strip()
        
        return jsonify({
            'printers': printers,
            'default': default_printer,
            'configured': Config.PRINTER_NAME
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print(f"🖨️  Print Server starting...")
    print(f"   Printer: {get_printer_name() or 'Not configured'}")
    print(f"   Port: {Config.PORT}")
    print(f"   Debug: {Config.DEBUG}")
    
    app.run(
        host='0.0.0.0',
        port=Config.PORT,
        debug=Config.DEBUG
    )

