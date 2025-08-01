#!/usr/bin/env python3
"""
Combined E-ink Display System Runner
Runs both the display monitor and upload server in parallel.
"""

import sys
import os
import time
import threading
import signal
import argparse
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_display_monitor(args):
    """Run the display monitor in a separate thread"""
    # Save original argv before any potential exceptions
    original_argv = sys.argv.copy()

    try:
        # Import and run display_latest
        import display_latest

        # Build arguments for display_latest
        display_args = ['display_latest.py']

        if args.folder:
            display_args.extend(['--folder', args.folder])
        if args.display_file:
            display_args.extend(['--display-file', args.display_file])
        if args.clear_start:
            display_args.append('--clear-start')
        if args.no_clear_exit:
            display_args.append('--no-clear-exit')
        if args.orientation:
            display_args.extend(['--orientation', args.orientation])
        if args.disable_startup_timer:
            display_args.extend(['--disable-startup-timer', args.disable_startup_timer])
        if args.disable_refresh_timer:
            display_args.extend(['--disable-refresh-timer', args.disable_refresh_timer])
        if args.refresh_interval:
            display_args.extend(['--refresh-interval', str(args.refresh_interval)])
        if args.startup_delay:
            display_args.extend(['--startup-delay', str(args.startup_delay)])
        if args.enable_manufacturer_timing:
            display_args.extend(['--enable-manufacturer-timing', args.enable_manufacturer_timing])
        if args.enable_sleep_mode:
            display_args.extend(['--enable-sleep-mode', args.enable_sleep_mode])

        sys.argv = display_args

        print("🖥️  Starting display monitor...")
        display_latest.main()

    except KeyboardInterrupt:
        print("Display monitor stopped by user")
    except Exception as e:
        print(f"Display monitor error: {e}")
    finally:
        # Restore original argv
        sys.argv = original_argv

def run_upload_server(args):
    """Run the upload server in a separate thread"""
    try:
        # Run upload server as subprocess instead of import
        import subprocess
        import sys

        print("🌐 Starting upload server...")

        # Run upload_server.py directly
        cmd = [sys.executable, 'upload_server.py']
        env = os.environ.copy()
        env['FLASK_HOST'] = '0.0.0.0'
        env['FLASK_PORT'] = str(args.port)

        subprocess.run(cmd, env=env, cwd=os.path.dirname(os.path.abspath(__file__)))

    except KeyboardInterrupt:
        print("Upload server stopped by user")
    except ImportError as e:
        print(f"❌ Upload server import error: {e}")
        print("   Check if Flask and other web dependencies are installed")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Upload server error: Port {args.port} is already in use")
            print(f"   Try a different port: --port {args.port + 1}")
        else:
            print(f"❌ Upload server OS error: {e}")
    except Exception as e:
        print(f"❌ Upload server error: {e}")
        import traceback
        traceback.print_exc()

# Global variables for exit handling
CLEAR_ON_EXIT = True
exit_requested = False

def signal_handler_clear_exit(signum, frame):
    """Handle Ctrl+C - exit with display clearing"""
    global exit_requested
    print("\n🛑 Ctrl+C pressed - shutting down e-ink system with display clearing...")
    exit_requested = True

    # Clean up display before exiting (if not disabled)
    if CLEAR_ON_EXIT:
        try:
            # Import and initialize EPD for cleanup using unified system
            from unified_epd_adapter import UnifiedEPD, EPDConfig
            display_type = EPDConfig.load_display_config()
            epd = UnifiedEPD.create_display(display_type)
            epd.init()
            epd.clear()
            epd.sleep()
            print("🖥️  Display cleared and put to sleep")
        except Exception as e:
            print(f"⚠️  Display cleanup error: {e}")
    else:
        try:
            # Just put display to sleep without clearing
            from unified_epd_adapter import UnifiedEPD, EPDConfig
            display_type = EPDConfig.load_display_config()
            epd = UnifiedEPD.create_display(display_type)
            epd.init()
            epd.sleep()
            print("🖥️  Display put to sleep (not cleared)")
        except Exception as e:
            print(f"⚠️  Display sleep error: {e}")

    # Give a moment for cleanup to complete
    time.sleep(1)
    os._exit(0)



def main():
    parser = argparse.ArgumentParser(
        description='Run E-ink Display System (Monitor + Upload Server)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Run with default settings
  %(prog)s -d welcome.jpg                     # Display welcome image on startup
  %(prog)s -f ~/display_files --port 8080     # Custom folder and port
  %(prog)s --clear-start --no-clear-exit      # Clear on start, leave on exit
        """
    )

    # Display monitor arguments
    parser.add_argument('--folder', '-f', default='~/watched_files',
                       help='Folder to monitor for files (default: ~/watched_files)')
    parser.add_argument('--display-file', '-d',
                       help='Display this file on startup and wait for new files')
    parser.add_argument('--clear-start', action='store_true',
                       help='Clear screen on start')
    parser.add_argument('--no-clear-exit', action='store_true',
                       help='Do not clear screen on exit')
    parser.add_argument('--orientation', choices=['landscape', 'landscape_flipped', 'portrait', 'portrait_flipped'],
                       help='Display orientation (default: landscape)')
    parser.add_argument('--disable-startup-timer', type=str, choices=['true', 'false'], default=None,
                       help='Set disable_startup_timer (true/false)')
    parser.add_argument('--disable-refresh-timer', type=str, choices=['true', 'false'], default=None,
                       help='Set disable_refresh_timer (true/false)')
    parser.add_argument('--refresh-interval', type=int, default=24,
                       help='Refresh interval in hours (default: 24)')
    parser.add_argument('--startup-delay', type=int, default=1,
                       help='Startup delay in minutes before displaying latest file (default: 1)')
    parser.add_argument('--enable-manufacturer-timing', type=str, choices=['true', 'false'], default=None,
                       help='Set enable_manufacturer_timing (true/false)')
    parser.add_argument('--enable-sleep-mode', type=str, choices=['true', 'false'], default=None,
                       help='Set enable_sleep_mode (true/false)')

    # Upload server arguments
    parser.add_argument('--port', '-p', type=int, default=5000,
                       help='Upload server port (default: 5000)')
    parser.add_argument('--server-only', action='store_true',
                       help='Run upload server only (no display monitor)')
    parser.add_argument('--monitor-only', action='store_true',
                       help='Run display monitor only (no upload server)')

    args = parser.parse_args()

    # Set global clear on exit flag
    global CLEAR_ON_EXIT
    CLEAR_ON_EXIT = not args.no_clear_exit

    # Handle signals for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler_clear_exit)      # Ctrl+C - clear and exit

    print("🚀 Starting E-ink Display System...")
    print(f"📁 Watched folder: {os.path.expanduser(args.folder)}")
    print(f"🌐 Upload server port: {args.port}")
    if args.no_clear_exit:
        print("🖥️  Display will NOT be cleared on exit")
        print("Press Ctrl+C to stop and clear display")

    threads = []

    try:
        # Start display monitor (unless server-only)
        if not args.server_only:
            monitor_thread = threading.Thread(
                target=run_display_monitor,
                args=(args,),
                daemon=True
            )
            monitor_thread.start()
            threads.append(monitor_thread)
            time.sleep(2)  # Give monitor time to start

        # Start upload server (unless monitor-only)
        if not args.monitor_only:
            server_thread = threading.Thread(
                target=run_upload_server,
                args=(args,),
                daemon=True
            )
            server_thread.start()
            threads.append(server_thread)
            time.sleep(2)  # Give server time to start

        print("✅ E-ink Display System is running!")
        print("   - Display monitor: Watching for new files")
        print("   - Upload server: Ready for TouchDesigner connections")

        # Keep main thread alive until exit is requested
        while not exit_requested:
            time.sleep(1)

            # Check if any thread has died
            for thread in threads:
                if not thread.is_alive():
                    print(f"⚠️  Thread {thread.name} has stopped")

    except KeyboardInterrupt:
        # This shouldn't happen anymore since we handle signals, but keep as fallback
        print("\n🛑 Stopping E-ink Display System...")
    except Exception as e:
        print(f"❌ System error: {e}")
    finally:
        print("👋 E-ink Display System stopped")

if __name__ == "__main__":
    main()
