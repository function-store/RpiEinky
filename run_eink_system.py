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
    try:
        # Import and run display_latest
        import display_latest
        
        # Override sys.argv for display_latest
        original_argv = sys.argv.copy()
        
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
        if args.normal_orientation:
            display_args.append('--normal-orientation')
            
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
        # Import and run upload_server
        import upload_server
        
        print("🌐 Starting upload server...")
        upload_server.app.run(
            host='0.0.0.0', 
            port=args.port, 
            debug=False,
            threaded=True
        )
        
    except KeyboardInterrupt:
        print("Upload server stopped by user")
    except Exception as e:
        print(f"Upload server error: {e}")

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\n🛑 Shutting down e-ink system...")
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
    parser.add_argument('--normal-orientation', action='store_true',
                       help='Display in normal orientation (not upside-down)')
    
    # Upload server arguments
    parser.add_argument('--port', '-p', type=int, default=5000,
                       help='Upload server port (default: 5000)')
    parser.add_argument('--server-only', action='store_true',
                       help='Run upload server only (no display monitor)')
    parser.add_argument('--monitor-only', action='store_true',
                       help='Run display monitor only (no upload server)')
    
    args = parser.parse_args()
    
    # Handle signal for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    
    print("🚀 Starting E-ink Display System...")
    print(f"📁 Watched folder: {os.path.expanduser(args.folder)}")
    print(f"🌐 Upload server port: {args.port}")
    
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
        print("   - Press Ctrl+C to stop")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            
            # Check if any thread has died
            for thread in threads:
                if not thread.is_alive():
                    print(f"⚠️  Thread {thread.name} has stopped")
                    
    except KeyboardInterrupt:
        print("\n🛑 Stopping E-ink Display System...")
    except Exception as e:
        print(f"❌ System error: {e}")
    finally:
        print("👋 E-ink Display System stopped")

if __name__ == "__main__":
    main() 