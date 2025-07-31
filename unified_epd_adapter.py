#!/usr/bin/python
# -*- coding:utf-8 -*-
"""
Unified E-Paper Display Adapter

This module provides a unified interface for different e-paper display types,
allowing the same code to work with various Waveshare displays.

Supported displays:
- epd2in15g (2.15" grayscale)
- epd13in3E (13.3" color)
- epd7in3e (7.3" color)

Usage:
    # For 2.15" display
    epd = UnifiedEPD.create_display("epd2in15g")
    
    # For 13.3" display  
    epd = UnifiedEPD.create_display("epd13in3E")
    
    # For 7.3" display
    epd = UnifiedEPD.create_display("epd7in3e")
    
    # Common interface
    epd.init()
    epd.display(image)
    epd.clear()
    epd.sleep()
"""

import sys
import os
import logging
from abc import ABC, abstractmethod
from typing import Union, Optional
from PIL import Image

logger = logging.getLogger(__name__)

class EPDAdapter(ABC):
    """Abstract base class for EPD adapters"""
    
    @abstractmethod
    def init(self) -> int:
        """Initialize the display"""
        pass
    
    @abstractmethod
    def display(self, image) -> None:
        """Display an image"""
        pass
    
    @abstractmethod
    def clear(self, color: Optional[int] = None) -> None:
        """Clear the display"""
        pass
    
    @abstractmethod
    def sleep(self) -> None:
        """Put display to sleep"""
        pass
    
    @abstractmethod
    def getbuffer(self, image: Image.Image):
        """Convert image to display buffer"""
        pass
    
    @property
    @abstractmethod
    def display_type(self) -> str:
        """Display type"""
        pass

    @property
    @abstractmethod
    def width(self) -> int:
        """Display width"""
        pass
    
    @property
    @abstractmethod
    def height(self) -> int:
        """Display height"""
        pass
    
    @property
    @abstractmethod
    def WHITE(self) -> int:
        """White color value"""
        pass
    
    @property
    @abstractmethod
    def BLACK(self) -> int:
        """Black color value"""
        pass
    
    @property
    @abstractmethod
    def RED(self) -> int:
        """Red color value"""
        pass
    
    @property
    @abstractmethod
    def YELLOW(self) -> int:
        """Yellow color value"""
        pass
    
    # Orientation-aware properties
    @property
    def native_orientation(self) -> str:
        """Get native orientation of the display"""
        # This will be overridden in concrete adapters
        return "landscape"
    
    @property
    def landscape_width(self) -> int:
        """Width when display is in landscape orientation"""
        if self.native_orientation == "landscape":
            return self.width
        else:
            return self.height
    
    @property 
    def landscape_height(self) -> int:
        """Height when display is in landscape orientation"""
        if self.native_orientation == "landscape":
            return self.height
        else:
            return self.width
    
    @property
    def portrait_width(self) -> int:
        """Width when display is in portrait orientation"""
        if self.native_orientation == "portrait":
            return self.width
        else:
            return self.height
    
    @property
    def portrait_height(self) -> int:
        """Height when display is in portrait orientation"""
        if self.native_orientation == "portrait":
            return self.height
        else:
            return self.width


class EPD2in15gAdapter(EPDAdapter):
    """Adapter for epd2in15g display"""
    
    def __init__(self):
        # Import the actual display module
        try:
            from waveshare_epd import epd2in15g
            self._epd = epd2in15g.EPD()
        except ImportError:
            logger.error("epd2in15g module not found. Make sure waveshare_epd is in your path.")
            raise
    
    @property
    def display_type(self) -> str:
        return "epd2in15g"
    
    def init(self) -> int:
        """Initialize the display"""
        return self._epd.init()
    
    def display(self, image) -> None:
        """Display an image"""
        self._epd.display(image)
    
    def clear(self, color: Optional[int] = None) -> None:
        """Clear the display"""
        if color is None:
            color = 0x55  # Default for 2in15g
        # Try both Clear and clear methods for compatibility
        if hasattr(self._epd, 'Clear'):
            self._epd.Clear(color)
        elif hasattr(self._epd, 'clear'):
            self._epd.clear(color)
        else:
            raise AttributeError(f"EPD object has neither 'Clear' nor 'clear' method")
    
    def Clear(self, color: Optional[int] = None) -> None:
        """Clear the display (uppercase for backward compatibility)"""
        self.clear(color)
    
    def sleep(self) -> None:
        """Put display to sleep"""
        self._epd.sleep()
    
    def getbuffer(self, image: Image.Image):
        """Convert image to display buffer"""
        return self._epd.getbuffer(image)
    
    @property
    def width(self) -> int:
        return self._epd.width
    
    @property
    def height(self) -> int:
        return self._epd.height
    
    @property
    def WHITE(self) -> int:
        return self._epd.WHITE
    
    @property
    def BLACK(self) -> int:
        return self._epd.BLACK
    
    @property
    def RED(self) -> int:
        return self._epd.RED
    
    @property
    def YELLOW(self) -> int:
        return self._epd.YELLOW
    
    @property
    def native_orientation(self) -> str:
        return "portrait"


class EPD13in3EAdapter(EPDAdapter):
    """Adapter for epd13in3E display"""
    
    def __init__(self):
        # Import the actual display module - 13.3" has different structure
        try:
            # First try the separate program structure (13.3" specific)
            import sys
            import os
            
            # Add the 13.3" library path to sys.path
            script_dir = os.path.dirname(os.path.abspath(__file__))
            epd13_path = os.path.join(script_dir, 'e-Paper', 'E-paper_Separate_Program', 
                                     '13.3inch_e-Paper_E', 'RaspberryPi', 'python', 'lib')
            
            logger.info(f"13.3\" library path in principle: {epd13_path}")
            
            if os.path.exists(epd13_path):
                sys.path.insert(0, epd13_path)
                import epd13in3E
                self._epd = epd13in3E.EPD()
                logger.info(f"Loaded 13.3\" display from separate program path: {epd13_path}")
            else:
                # Fallback to waveshare_epd structure
                from waveshare_epd import epd13in3E
                self._epd = epd13in3E.EPD()
                logger.info("Loaded 13.3\" display from waveshare_epd")
                
        except ImportError as e:
            logger.error(f"epd13in3E module not found. Error: {e}")
            logger.error("For 13.3\" display, ensure the library is installed from:")
            logger.error("e-Paper/E-paper_Separate_Program/13.3inch_e-Paper_E/RaspberryPi/python/lib/")
            raise
    
    @property
    def display_type(self) -> str:
        return "epd13in3E"
    
    def init(self) -> int:
        """Initialize the display"""
        return self._epd.Init()  # Note: capital I
    
    def display(self, image) -> None:
        """Display an image"""
        self._epd.display(image)
    
    def clear(self, color: Optional[int] = None) -> None:
        """Clear the display"""
        if color is None:
            color = 0x11  # Default for 13in3E
        # Try both Clear and clear methods for compatibility
        if hasattr(self._epd, 'Clear'):
            self._epd.Clear(color)
        elif hasattr(self._epd, 'clear'):
            self._epd.clear(color)
        else:
            raise AttributeError(f"EPD object has neither 'Clear' nor 'clear' method")
    
    def Clear(self, color: Optional[int] = None) -> None:
        """Clear the display (uppercase for backward compatibility)"""
        self.clear(color)
    
    def sleep(self) -> None:
        """Put display to sleep"""
        self._epd.sleep()
    
    def getbuffer(self, image: Image.Image):
        """Convert image to display buffer"""
        return self._epd.getbuffer(image)
    
    @property
    def width(self) -> int:
        return self._epd.width
    
    @property
    def height(self) -> int:
        return self._epd.height
    
    @property
    def WHITE(self) -> int:
        return self._epd.WHITE
    
    @property
    def BLACK(self) -> int:
        return self._epd.BLACK
    
    @property
    def RED(self) -> int:
        return self._epd.RED
    
    @property
    def YELLOW(self) -> int:
        return self._epd.YELLOW
    
    @property
    def native_orientation(self) -> str:
        return "portrait"


class EPD7in3eAdapter(EPDAdapter):
    """Adapter for epd7in3e display"""
    
    def __init__(self):
        # Import the actual display module
        try:
            from waveshare_epd import epd7in3e
            self._epd = epd7in3e.EPD()
        except ImportError:
            logger.error("epd7in3e module not found. Make sure waveshare_epd is in your path.")
            raise
    
    @property
    def display_type(self) -> str:
        return "epd7in3e"
    
    def init(self) -> int:
        """Initialize the display"""
        return self._epd.init()
    
    def display(self, image) -> None:
        """Display an image"""
        self._epd.display(image)
    
    def clear(self, color: Optional[int] = None) -> None:
        """Clear the display"""
        if color is None:
            color = 0x11  # Default for 7in3e
        # Try both Clear and clear methods for compatibility
        if hasattr(self._epd, 'Clear'):
            self._epd.Clear(color)
        elif hasattr(self._epd, 'clear'):
            self._epd.clear(color)
        else:
            raise AttributeError(f"EPD object has neither 'Clear' nor 'clear' method")
    
    def Clear(self, color: Optional[int] = None) -> None:
        """Clear the display (uppercase for backward compatibility)"""
        self.clear(color)
    
    def sleep(self) -> None:
        """Put display to sleep"""
        self._epd.sleep()
    
    def getbuffer(self, image: Image.Image):
        """Convert image to display buffer"""
        return self._epd.getbuffer(image)
    
    @property
    def width(self) -> int:
        return self._epd.width
    
    @property
    def height(self) -> int:
        return self._epd.height
    
    @property
    def WHITE(self) -> int:
        return self._epd.WHITE
    
    @property
    def BLACK(self) -> int:
        return self._epd.BLACK
    
    @property
    def RED(self) -> int:
        return self._epd.RED
    
    @property
    def YELLOW(self) -> int:
        return self._epd.YELLOW
    
    @property
    def native_orientation(self) -> str:
        # we say this even though it's portrait, because in the library the width and height are swapped
        return "landscape"



class UnifiedEPD:
    """Factory class for creating unified EPD instances"""
    
    # Display configuration database
    DISPLAY_CONFIGS = {
        "epd2in15g": {
            "class": EPD2in15gAdapter,
            "name": "2.15\" Grayscale Display",
            "resolution": (296, 120),
            "colors": "4-color grayscale",
            "native_orientation": "portrait"
        },
        "epd13in3E": {
            "class": EPD13in3EAdapter,
            "name": "13.3\" Color Display", 
            "resolution": (1600, 1200),
            "colors": "7-color",
            "native_orientation": "portrait"
        },
        "epd7in3e": {
            "class": EPD7in3eAdapter,
            "name": "7.3\" Color Display",
            "resolution": (800, 480),
            "colors": "7-color",
            "native_orientation": "landscape"
        }
    }
    
    @classmethod
    def create_display(cls, display_type: str) -> EPDAdapter:
        """
        Create a unified EPD instance based on display type
        
        Args:
            display_type: Type of display ("epd2in15g" or "epd13in3E")
            
        Returns:
            EPDAdapter instance
            
        Raises:
            ValueError: If display type is not supported
        """
        if display_type not in cls.DISPLAY_CONFIGS:
            supported = ", ".join(cls.DISPLAY_CONFIGS.keys())
            raise ValueError(f"Unsupported display type: {display_type}. Supported types: {supported}")
        
        config = cls.DISPLAY_CONFIGS[display_type]
        adapter_class = config["class"]
        
        width, height = config['resolution']
        logger.info(f"Creating {config['name']} ({width}x{height}, {config['colors']})")
        return adapter_class()
    
    @classmethod
    def list_supported_displays(cls) -> dict:
        """List all supported display types and their configurations"""
        return cls.DISPLAY_CONFIGS.copy()
    
    @classmethod
    def get_display_info(cls, display_type: str) -> Optional[dict]:
        """Get information about a specific display type"""
        return cls.DISPLAY_CONFIGS.get(display_type)
    
    @classmethod
    def get_display_resolution(cls, display_type: str) -> Optional[tuple]:
        """Get resolution as (width, height) tuple for a display type"""
        config = cls.DISPLAY_CONFIGS.get(display_type)
        return config['resolution'] if config else None
    
    @classmethod
    def get_display_dimensions(cls, display_type: str) -> Optional[tuple]:
        """Get display dimensions as (width, height) tuple (alias for get_display_resolution)"""
        return cls.get_display_resolution(display_type)
    
    @classmethod
    def get_display_pixel_count(cls, display_type: str) -> Optional[int]:
        """Get total pixel count (width * height) for a display type"""
        config = cls.DISPLAY_CONFIGS.get(display_type)
        if config:
            width, height = config['resolution']
            return width * height
        return None
    
    @classmethod
    def get_landscape_dimensions(cls, display_type: str) -> Optional[tuple]:
        """Get landscape dimensions (width, height) for a display type"""
        config = cls.DISPLAY_CONFIGS.get(display_type)
        if config:
            width, height = config['resolution']
            native_orientation = config.get('native_orientation', 'landscape')
            if native_orientation == 'landscape':
                return (width, height)  # Already landscape
            else:
                return (height, width)  # Swap for portrait-native displays
        return None
    
    @classmethod
    def get_portrait_dimensions(cls, display_type: str) -> Optional[tuple]:
        """Get portrait dimensions (width, height) for a display type"""
        config = cls.DISPLAY_CONFIGS.get(display_type)
        if config:
            width, height = config['resolution']
            native_orientation = config.get('native_orientation', 'landscape')
            if native_orientation == 'portrait':
                return (width, height)  # Already portrait
            else:
                return (height, width)  # Swap for landscape-native displays
        return None
    
    @classmethod
    def get_native_orientation(cls, display_type: str) -> Optional[str]:
        """Get native orientation for a display type"""
        config = cls.DISPLAY_CONFIGS.get(display_type)
        return config.get('native_orientation') if config else None


# Configuration helper
class EPDConfig:
    """Configuration management for EPD displays"""
    
    @staticmethod
    def load_display_config() -> str:
        """
        Load display type from configuration file
        
        Returns:
            Display type string
        """
        # Try multiple possible locations for config file
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_locations = [
            os.path.join(script_dir, '.epd_config.json'),  # Same directory as script
        ]
        
        config_file = None
        for location in config_locations:
            if os.path.exists(location):
                config_file = location
                logger.info(f"Found config file: {config_file}")
                # content of config_file
                with open(config_file, 'r') as f:
                    logger.info(f"Content of config file: {f.read()}")
                break
        
        try:
            if config_file:
                import json
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    display_type = config.get('display_type', 'epd2in15g')
                    logger.info(f"Loaded display config: {display_type} from {config_file}")
                    return display_type
        except Exception as e:
            logger.warning(f"Could not load display config: {e}")
        
        # Default to 2.15" display
        logger.info("Using default display type: epd2in15g")
        return 'epd2in15g'
    
    @staticmethod
    def save_display_config(display_type: str) -> None:
        """
        Save display type to configuration file
        
        Args:
            display_type: Type of display to save
        """
        # Save to same directory as script by default
        script_dir = os.path.dirname(os.path.abspath(__file__))
        config_file = os.path.join(script_dir, '.epd_config.json')
        
        try:
            import json
            config = {'display_type': display_type}
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(config_file), exist_ok=True)
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Saved display config: {display_type}")
        except Exception as e:
            logger.error(f"Could not save display config: {e}")


# Convenience function for easy usage
def create_epd(display_type: Optional[str] = None) -> EPDAdapter:
    """
    Create an EPD instance with automatic configuration loading
    
    Args:
        display_type: Optional display type. If None, loads from config file
        
    Returns:
        EPDAdapter instance
    """
    if display_type is None:
        display_type = EPDConfig.load_display_config()
    
    return UnifiedEPD.create_display(display_type)


# Example usage and testing
if __name__ == "__main__":
    # Test the unified interface
    logging.basicConfig(level=logging.INFO)
    
    print("Available displays:")
    for display_type, config in UnifiedEPD.list_supported_displays().items():
        width, height = config['resolution']
        pixel_count = width * height
        print(f"  {display_type}: {config['name']} ({width}x{height}, {pixel_count:,} pixels)")
    
    print("\nTesting display creation...")
    
    try:
        # Test 2.15" display
        print("Testing epd2in15g...")
        epd1 = UnifiedEPD.create_display("epd2in15g")
        print(f"  Created: {epd1.width}x{epd1.height}")
        
        # Test 13.3" display
        print("Testing epd13in3E...")
        epd2 = UnifiedEPD.create_display("epd13in3E")
        print(f"  Created: {epd2.width}x{epd2.height}")
        
        # Test 7.3" display
        print("Testing epd7in3e...")
        epd3 = UnifiedEPD.create_display("epd7in3e")
        print(f"  Created: {epd3.width}x{epd3.height}")
        
        print("All tests passed!")
        
        # Test utility methods
        print("\nTesting utility methods...")
        for display_type in ["epd2in15g", "epd13in3E", "epd7in3e"]:
            resolution = UnifiedEPD.get_display_resolution(display_type)
            pixel_count = UnifiedEPD.get_display_pixel_count(display_type)
            print(f"  {display_type}: {resolution} = {pixel_count:,} pixels")
        
    except Exception as e:
        print(f"Test failed: {e}")
        print("This is expected if the display modules are not available in the current environment.") 
        