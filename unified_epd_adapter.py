#!/usr/bin/python
# -*- coding:utf-8 -*-
"""
Unified E-Paper Display Adapter

This module provides a unified interface for different e-paper display types,
allowing the same code to work with various Waveshare displays.

Supported displays:
- epd2in15g (2.15" grayscale)
- epd13in3E (13.3" color)

Usage:
    # For 2.15" display
    epd = UnifiedEPD.create_display("epd2in15g")
    
    # For 13.3" display  
    epd = UnifiedEPD.create_display("epd13in3E")
    
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
        self._epd.Clear(color)
    
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


class EPD13in3EAdapter(EPDAdapter):
    """Adapter for epd13in3E display"""
    
    def __init__(self):
        # Import the actual display module
        try:
            import epd13in3E
            self._epd = epd13in3E.EPD()
        except ImportError:
            logger.error("epd13in3E module not found. Make sure it's in your path.")
            raise
    
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
        self._epd.Clear(color)
    
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


class UnifiedEPD:
    """Factory class for creating unified EPD instances"""
    
    # Display configuration database
    DISPLAY_CONFIGS = {
        "epd2in15g": {
            "class": EPD2in15gAdapter,
            "name": "2.15\" Grayscale Display",
            "resolution": "160x296",
            "colors": "4-color grayscale"
        },
        "epd13in3E": {
            "class": EPD13in3EAdapter,
            "name": "13.3\" Color Display", 
            "resolution": "1200x1600",
            "colors": "7-color"
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
        
        logger.info(f"Creating {config['name']} ({config['resolution']}, {config['colors']})")
        return adapter_class()
    
    @classmethod
    def list_supported_displays(cls) -> dict:
        """List all supported display types and their configurations"""
        return cls.DISPLAY_CONFIGS.copy()
    
    @classmethod
    def get_display_info(cls, display_type: str) -> Optional[dict]:
        """Get information about a specific display type"""
        return cls.DISPLAY_CONFIGS.get(display_type)


# Backward compatibility wrapper for existing code
class LegacyEPDWrapper:
    """Wrapper that provides the same interface as the original EPD classes"""
    
    def __init__(self, display_type: str):
        self._adapter = UnifiedEPD.create_display(display_type)
        
        # Expose adapter properties as instance attributes for compatibility
        self.width = self._adapter.width
        self.height = self._adapter.height
        self.WHITE = self._adapter.WHITE
        self.BLACK = self._adapter.BLACK
        self.RED = self._adapter.RED
        self.YELLOW = self._adapter.YELLOW
    
    def init(self) -> int:
        """Initialize the display (compatible with both naming conventions)"""
        return self._adapter.init()
    
    def Init(self) -> int:
        """Alternative init method for compatibility"""
        return self._adapter.init()
    
    def display(self, image) -> None:
        """Display an image"""
        self._adapter.display(image)
    
    def Clear(self, color=None) -> None:
        """Clear the display (compatible with both naming conventions)"""
        self._adapter.clear(color)
    
    def clear(self, color=None) -> None:
        """Alternative clear method for compatibility"""
        self._adapter.clear(color)
    
    def sleep(self) -> None:
        """Put display to sleep"""
        self._adapter.sleep()
    
    def getbuffer(self, image: Image.Image):
        """Convert image to display buffer"""
        return self._adapter.getbuffer(image)


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
        config_file = os.path.expanduser("~/watched_files/.epd_config.json")
        
        try:
            if os.path.exists(config_file):
                import json
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    display_type = config.get('display_type', 'epd2in15g')
                    logger.info(f"Loaded display config: {display_type}")
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
        config_file = os.path.expanduser("~/watched_files/.epd_config.json")
        
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
        print(f"  {display_type}: {config['name']} ({config['resolution']})")
    
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
        
        print("All tests passed!")
        
    except Exception as e:
        print(f"Test failed: {e}")
        print("This is expected if the display modules are not available in the current environment.") 