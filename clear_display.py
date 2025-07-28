#!/usr/bin/python
# -*- coding:utf-8 -*-
"""
Simple script to clear the e-ink display
"""
import sys
import os
import time

# Setup paths like in the test file
libdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'lib')
if os.path.exists(libdir):
    sys.path.append(libdir)

from unified_epd_adapter import UnifiedEPD, EPDConfig

def clear_display():
    """Clear the e-ink display"""
    try:
        print("🖥️  Initializing e-ink display...")
        display_type = EPDConfig.load_display_config()
        epd = UnifiedEPD.create_display(display_type)
        epd.init()
        
        print("🧹 Clearing display...")
        epd.clear()
        
        print("💤 Putting display to sleep...")
        epd.sleep()
        
        print("✅ Display cleared successfully!")
        
    except Exception as e:
        print(f"❌ Error clearing display: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("E-ink Display Clear Script")
    print("=" * 30)
    clear_display() 