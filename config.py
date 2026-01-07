"""
Configuration for the Print Server.
Edit these values for your setup.
"""

import os
import secrets


class Config:
    # ==========================================================================
    # API KEY - CHANGE THIS!
    # ==========================================================================
    # Generate a new key with: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
    API_KEY = os.environ.get('PRINT_API_KEY', 'CHANGE_ME_GENERATE_A_SECURE_KEY')
    
    # ==========================================================================
    # PRINTER SETTINGS
    # ==========================================================================
    # Leave empty to use the system default printer
    # Run 'lpstat -p -d' to see available printers
    PRINTER_NAME = os.environ.get('PRINTER_NAME', '')
    
    # Additional print options (passed to lp -o)
    # Examples: 'fit-to-page', 'media=A4', 'orientation-requested=4'
    # For borderless printing, use 'media=A4.Borderless' or 'media=Letter.Borderless'
    PRINT_OPTIONS = [
        'fit-to-page',           # Scale image to fit the page
        'media=A4.Borderless',   # Borderless A4 printing (change to Letter.Borderless for US)
    ]
    
    # Maximum copies allowed per request (prevent abuse)
    MAX_COPIES = 10
    
    # ==========================================================================
    # SERVER SETTINGS
    # ==========================================================================
    PORT = int(os.environ.get('PRINT_SERVER_PORT', 3000))
    DEBUG = os.environ.get('PRINT_SERVER_DEBUG', 'false').lower() == 'true'
    
    # ==========================================================================
    # FILE SETTINGS
    # ==========================================================================
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

