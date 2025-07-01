"""
Simple favicon generator for Crucible Platform.
Creates a minimal favicon programmatically.
"""


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
    Creates a simple flask/beaker icon for the evaluation platform.
    """
    return '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">
  <defs>
    <linearGradient id="bg-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#4F46E5;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#7C3AED;stop-opacity:1" />
    </linearGradient>
  </defs>
  <!-- Background -->
  <rect width="32" height="32" fill="url(#bg-gradient)" rx="6"/>
  
  <!-- Flask/Beaker Icon -->
  <g transform="translate(16, 16)">
    <!-- Flask body -->
    <path d="M -6,0 L -6,-7 L -4,-7 L -4,-2 L -7,6 C -7,7 -6,8 -5,8 L 5,8 C 6,8 7,7 7,6 L 4,-2 L 4,-7 L 6,-7 L 6,0 L 9,8 C 9,10 7,11 5,11 L -5,11 C -7,11 -9,10 -9,8 Z" 
          fill="white" 
          opacity="0.95"/>
    
    <!-- Liquid inside -->
    <path d="M -5,3 L -6,6 C -6,6.5 -5.5,7 -5,7 L 5,7 C 5.5,7 6,6.5 6,6 L 5,3 C 4,4 -4,4 -5,3 Z" 
          fill="#4F46E5" 
          opacity="0.5"/>
    
    <!-- Bubbles -->
    <circle cx="-2" cy="5" r="0.8" fill="white" opacity="0.7"/>
    <circle cx="1" cy="4.5" r="0.5" fill="white" opacity="0.7"/>
    <circle cx="2.5" cy="6" r="0.6" fill="white" opacity="0.7"/>
  </g>
</svg>'''

def get_favicon_bytes() -> bytes:
    """
    Returns raw favicon bytes for ICO format.
    Creates a simple 16x16 purple gradient icon.
    """
    # Simple 16x16 ICO file with purple gradient
    # ICO header
    ico_header = bytes([
        0x00, 0x00,  # Reserved
        0x01, 0x00,  # Type (1 = ICO)
        0x01, 0x00,  # Number of images (1)
    ])
    
    # ICO directory entry
    ico_dir = bytes([
        0x10,        # Width (16)
        0x10,        # Height (16)
        0x00,        # Color palette (0 = no palette)
        0x00,        # Reserved
        0x01, 0x00,  # Color planes (1)
        0x20, 0x00,  # Bits per pixel (32)
        0x68, 0x04, 0x00, 0x00,  # Image size (1128 bytes)
        0x16, 0x00, 0x00, 0x00,  # Image offset (22 bytes)
    ])
    
    # BMP header
    bmp_header = bytes([
        0x28, 0x00, 0x00, 0x00,  # Header size (40)
        0x10, 0x00, 0x00, 0x00,  # Width (16)
        0x20, 0x00, 0x00, 0x00,  # Height (32 = 2x for mask)
        0x01, 0x00,              # Planes (1)
        0x20, 0x00,              # Bits per pixel (32)
        0x00, 0x00, 0x00, 0x00,  # Compression (none)
        0x00, 0x04, 0x00, 0x00,  # Image size
        0x00, 0x00, 0x00, 0x00,  # X pixels per meter
        0x00, 0x00, 0x00, 0x00,  # Y pixels per meter
        0x00, 0x00, 0x00, 0x00,  # Colors used
        0x00, 0x00, 0x00, 0x00,  # Important colors
    ])
    
    # Create 16x16 purple gradient pixels (BGRA format)
    pixels = []
    for y in range(16):
        for x in range(16):
            # Gradient from #4F46E5 to #7C3AED
            t = (x + y) / 30.0  # Diagonal gradient
            r = int(79 + (124 - 79) * t)
            g = int(70 + (58 - 70) * t)
            b = int(229 + (237 - 229) * t)
            pixels.extend([b, g, r, 255])  # BGRA
    
    # AND mask (all transparent = all 0s for 32-bit)
    mask = bytes([0x00] * 64)
    
    return ico_header + ico_dir + bmp_header + bytes(pixels) + mask