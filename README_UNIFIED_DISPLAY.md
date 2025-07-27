# Unified E-Paper Display System

This system provides a unified interface for different e-paper display types, allowing the same code to work with various Waveshare displays without modification.

## Supported Displays

- **epd2in15g**: 2.15" Grayscale Display (160x296, 4-color grayscale)
- **epd13in3E**: 13.3" Color Display (1200x1600, 7-color)

## Quick Start

### 1. Configuration

The display type is configured via a JSON file at `~/watched_files/.epd_config.json`:

```json
{
  "display_type": "epd2in15g"
}
```

### 2. Using the Unified Display

#### Option A: Automatic Configuration Loading

```python
from unified_epd_adapter import create_epd

# Automatically loads display type from config file
epd = create_epd()

# Use the display
epd.init()
epd.display(image)
epd.clear()
epd.sleep()
```

#### Option B: Explicit Display Type

```python
from unified_epd_adapter import UnifiedEPD

# Create specific display type
epd = UnifiedEPD.create_display("epd13in3E")

# Use the display
epd.init()
epd.display(image)
epd.clear()
epd.sleep()
```

#### Option C: Backward Compatibility

```python
from unified_epd_adapter import LegacyEPDWrapper

# Works exactly like the original EPD classes
epd = LegacyEPDWrapper("epd2in15g")
epd.init()
epd.display(image)
epd.Clear()  # Note: both Clear() and clear() work
epd.sleep()
```

## Modified display_latest.py

The `display_latest.py` script has been updated to use the unified display system:

### New Command Line Options

```bash
# Use specific display type
python display_latest.py --display-type epd13in3E

# Use display type from config file (default)
python display_latest.py
```

### Configuration Management

```python
from unified_epd_adapter import EPDConfig

# Save display type
EPDConfig.save_display_config("epd13in3E")

# Load display type
display_type = EPDConfig.load_display_config()
```

## Testing

Run the test script to verify everything works:

```bash
python test_unified_display.py
```

This will:
1. Test display creation for all supported types
2. Test configuration loading/saving
3. Test basic display operations

## Architecture

### Adapter Pattern

The system uses the Adapter pattern to provide a unified interface:

```
EPDAdapter (Abstract Base Class)
├── EPD2in15gAdapter (2.15" display)
└── EPD13in3EAdapter (13.3" display)
```

### Factory Pattern

The `UnifiedEPD` factory class handles display creation:

```python
# Factory creates appropriate adapter
epd = UnifiedEPD.create_display("epd2in15g")
```

### Configuration Management

The `EPDConfig` class handles loading/saving display preferences:

```python
# Load from ~/watched_files/.epd_config.json
display_type = EPDConfig.load_display_config()
```

## Key Differences Handled

### Method Naming
- `epd2in15g`: `init()`, `reset()`, `send_command()`
- `epd13in3E`: `Init()`, `Reset()`, `SendCommand()`

### Color Definitions
- `epd2in15g`: 4-color grayscale (WHITE, BLACK, RED, YELLOW)
- `epd13in3E`: 7-color (WHITE, BLACK, RED, YELLOW, BLUE, GREEN, etc.)

### Display Resolution
- `epd2in15g`: 160x296
- `epd13in3E`: 1200x1600

### Buffer Handling
- Different `getbuffer()` implementations for each display type

## Migration Guide

### From Original display_latest.py

**Before:**
```python
from waveshare_epd import epd2in15g
self.epd = epd2in15g.EPD()
```

**After:**
```python
from unified_epd_adapter import UnifiedEPD, EPDConfig
display_type = EPDConfig.load_display_config()
self.epd = UnifiedEPD.create_display(display_type)
```

### From epd_13in3E_test.py

**Before:**
```python
import epd13in3E
epd = epd13in3E.EPD()
epd.Init()  # Note: capital I
```

**After:**
```python
from unified_epd_adapter import UnifiedEPD
epd = UnifiedEPD.create_display("epd13in3E")
epd.init()  # Note: lowercase i
```

## Adding New Display Types

To add support for a new display type:

1. **Create an adapter class:**
```python
class EPDNewDisplayAdapter(EPDAdapter):
    def __init__(self):
        import new_display_module
        self._epd = new_display_module.EPD()
    
    def init(self) -> int:
        return self._epd.init()  # or Init() depending on the module
    
    # Implement other abstract methods...
```

2. **Add to the factory:**
```python
DISPLAY_CONFIGS = {
    # ... existing configs ...
    "new_display": {
        "class": EPDNewDisplayAdapter,
        "name": "New Display",
        "resolution": "800x600",
        "colors": "monochrome"
    }
}
```

## Benefits

1. **Code Reuse**: Same code works with different displays
2. **Easy Configuration**: Simple JSON config file
3. **Backward Compatibility**: Existing code continues to work
4. **Extensible**: Easy to add new display types
5. **Type Safety**: Abstract base class ensures consistent interface
6. **Error Handling**: Graceful fallbacks and error messages

## Troubleshooting

### Import Errors

If you get import errors for display modules:

1. **For epd2in15g**: Make sure `waveshare_epd` is in your Python path
2. **For epd13in3E**: Make sure the module is in your Python path

### Configuration Issues

If the wrong display type is loaded:

1. Check `~/watched_files/.epd_config.json`
2. Use `--display-type` command line option to override
3. Use `EPDConfig.save_display_config()` to update the config

### Display Not Working

1. Run `test_unified_display.py` to verify the display works
2. Check that the correct display type is configured
3. Verify hardware connections and permissions 