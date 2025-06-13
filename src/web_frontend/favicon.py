"""
Simple favicon generator for Crucible Platform.
Creates a minimal favicon programmatically.
"""

import base64

def get_favicon_base64() -> str:
    """
    Returns a base64-encoded favicon.
    This is a simple 16x16 PNG converted to ICO format.
    """
    # This is a simple favicon - blue background with white C
    # Using a cleaner, simpler design
    favicon_base64 = (
        "AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAIAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAARkb//0ZG//9GRv//Rkb//0ZG//9GRv//Rkb//0ZG//9GRv//Rkb//0ZG//9GRv//AA"
        "AAAAAAAAAAAABGRv//Rkb//0ZG//9GRv//Rkb//0ZG//9GRv//Rkb//0ZG//9GRv//Rkb//0ZG//8A"
        "AAAAAAAAAAAAAEZG//9GRv//////////////////////////////////Rkb//0ZG//9GRv//Rkb//w"
        "AAAAAAAAAAAABGRv//Rkb///////////////////////////////////9GRv//Rkb//0ZG//9GRv//AA"
        "AAAAAAAAAAAABGRv//Rkb/////////////Rkb//0ZG//9GRv//Rkb//0ZG//9GRv//Rkb//0ZG//8AAA"
        "AAAAAAAAAAAEZG//9GRv///////0ZG//9GRv//Rkb//0ZG//9GRv//Rkb//0ZG//9GRv//Rkb//wAAAA"
        "AAAAAAAAAAAABGRv//Rkb///////9GRv//Rkb//0ZG//9GRv//Rkb//0ZG//9GRv//Rkb//0ZG//8AAA"
        "AAAAAAAAAAAEZG//9GRv///////0ZG//9GRv//Rkb//0ZG//9GRv//Rkb//0ZG//9GRv//Rkb//wAAAA"
        "AAAAAAAAAAAABGRv//Rkb/////////////Rkb//0ZG//9GRv//Rkb//0ZG//9GRv//Rkb//0ZG//8AAA"
        "AAAAAAAAAAAEZG//9GRv//////////////////////////////////Rkb//0ZG//9GRv//Rkb//wAAAA"
        "AAAAAAAAAAAABGRv//Rkb//////////////////////////////////0ZG//9GRv//Rkb//0ZG//8AAA"
        "AAAAAAAAAAAEZG//9GRv//Rkb//0ZG//9GRv//Rkb//0ZG//9GRv//Rkb//0ZG//9GRv//Rkb//wAAAA"
        "AAAAAAAAAAAABGRv//Rkb//0ZG//9GRv//Rkb//0ZG//9GRv//Rkb//0ZG//9GRv//Rkb//0ZG//8AAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AAD//wAA+A8AAPgPAADAAwAAwAMAAMADAADAAwAAwAMAAMADAADAAwAAwAMAAMADAADgBwAA+A8AAP"
        "gPAAD//wAA"
    )
    
    return favicon_base64

def get_svg_favicon() -> str:
    """
    Returns an SVG favicon as a string.
    This creates a simple 'C' logo for Crucible with better design.
    """
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <defs>
    <linearGradient id="bg-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#0066cc;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#004499;stop-opacity:1" />
    </linearGradient>
  </defs>
  <rect width="32" height="32" fill="url(#bg-gradient)" rx="6"/>
  <path d="M 16,6 C 11,6 8,10 8,16 C 8,22 11,26 16,26 C 19,26 21,24.5 22,22 L 18,22 C 17.5,23 17,23.5 16,23.5 C 13,23.5 11.5,21 11.5,16 C 11.5,11 13,8.5 16,8.5 C 17,8.5 17.5,9 18,10 L 22,10 C 21,7.5 19,6 16,6 Z" fill="white" stroke="none"/>
</svg>'''

def get_favicon_bytes() -> bytes:
    """
    Returns raw favicon bytes for ICO format.
    """
    return base64.b64decode(get_favicon_base64())