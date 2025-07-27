#!/usr/bin/python
# -*- coding:utf-8 -*-
"""
Test script for unified E-Paper display functionality

This script demonstrates how to use the unified display adapter
with different display types.
"""

import sys
import os
import logging
from pathlib import Path

# Setup paths
picdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'pic')
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

# Import the unified adapter
from unified_epd_adapter import UnifiedEPD, EPDConfig

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_display_creation():
    """Test creating different display types"""
    print("Testing display creation...")
    
    # List available displays
    print("\nAvailable displays:")
    for display_type, config in UnifiedEPD.list_supported_displays().items():
        print(f"  {display_type}: {config['name']} ({config['resolution']})")
    
    # Test each display type
    for display_type in UnifiedEPD.list_supported_displays().keys():
        try:
            print(f"\nTesting {display_type}...")
            epd = UnifiedEPD.create_display(display_type)
            print(f"  ✓ Created successfully: {epd.width}x{epd.height}")
            print(f"  ✓ Colors: WHITE={epd.WHITE}, BLACK={epd.BLACK}, RED={epd.RED}, YELLOW={epd.YELLOW}")
        except Exception as e:
            print(f"  ✗ Failed to create {display_type}: {e}")

def test_config_loading():
    """Test configuration loading and saving"""
    print("\nTesting configuration management...")
    
    # Test loading config
    display_type = EPDConfig.load_display_config()
    print(f"  Loaded display type: {display_type}")
    
    # Test saving config
    test_type = "epd13in3E"
    EPDConfig.save_display_config(test_type)
    print(f"  Saved display type: {test_type}")
    
    # Test loading again
    loaded_type = EPDConfig.load_display_config()
    print(f"  Reloaded display type: {loaded_type}")
    
    # Restore original
    EPDConfig.save_display_config(display_type)
    print(f"  Restored original display type: {display_type}")

def test_display_operations():
    """Test basic display operations"""
    print("\nTesting display operations...")
    
    try:
        # Load display type from config
        display_type = EPDConfig.load_display_config()
        print(f"  Using display type: {display_type}")
        
        # Create display
        epd = UnifiedEPD.create_display(display_type)
        print(f"  ✓ Display created: {epd.width}x{epd.height}")
        
        # Initialize display
        result = epd.init()
        print(f"  ✓ Display initialized: {result}")
        
        # Test getbuffer with a simple image
        from PIL import Image, ImageDraw, ImageFont
        
        # Create a test image
        image = Image.new('RGB', (epd.width, epd.height), epd.WHITE)
        draw = ImageDraw.Draw(image)
        
        # Add some text
        try:
            font = ImageFont.truetype(os.path.join(picdir, 'Font.ttc'), 20)
        except:
            font = ImageFont.load_default()
        
        draw.text((10, 10), f"Test: {display_type}", font=font, fill=epd.BLACK)
        draw.text((10, 40), f"Size: {epd.width}x{epd.height}", font=font, fill=epd.RED)
        draw.text((10, 70), "Unified Adapter Test", font=font, fill=epd.YELLOW)
        
        # Convert to buffer
        buffer = epd.getbuffer(image)
        print(f"  ✓ Image converted to buffer: {len(buffer)} bytes")
        
        # Display the image
        epd.display(buffer)
        print("  ✓ Image displayed successfully")
        
        # Wait a moment
        import time
        time.sleep(3)
        
        # Clear display
        epd.clear()
        print("  ✓ Display cleared")
        
        # Sleep
        epd.sleep()
        print("  ✓ Display put to sleep")
        
    except Exception as e:
        print(f"  ✗ Display operations failed: {e}")
        logger.exception("Display operations error")

def main():
    """Main test function"""
    print("Unified E-Paper Display Adapter Test")
    print("=" * 50)
    
    # Test display creation
    test_display_creation()
    
    # Test configuration management
    test_config_loading()
    
    # Test display operations
    test_display_operations()
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    main() 