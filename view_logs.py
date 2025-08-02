#!/usr/bin/env python3
"""
Simple log viewer for Maybank Parser logs.
"""

import os
import sys
from datetime import datetime

def view_logs(lines=50):
    """View the last N lines of the log file."""
    log_file = "logs/maybank_parser.log"
    
    if not os.path.exists(log_file):
        print("❌ No log file found. Run the parser first to generate logs.")
        return
    
    try:
        with open(log_file, 'r') as f:
            all_lines = f.readlines()
        
        if not all_lines:
            print("📝 Log file is empty.")
            return
        
        # Get the last N lines
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        print(f"📋 Last {len(recent_lines)} lines from {log_file}:")
        print("=" * 60)
        
        for line in recent_lines:
            print(line.rstrip())
        
        print("=" * 60)
        print(f"📊 Total lines in log: {len(all_lines)}")
        
        # Show file info
        stat = os.stat(log_file)
        mod_time = datetime.fromtimestamp(stat.st_mtime)
        print(f"📅 Last modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📏 File size: {stat.st_size} bytes")
        
    except Exception as e:
        print(f"❌ Error reading log file: {e}")

def clear_logs():
    """Clear the log file."""
    log_file = "logs/maybank_parser.log"
    
    if not os.path.exists(log_file):
        print("❌ No log file found to clear.")
        return
    
    try:
        with open(log_file, 'w') as f:
            f.write('')  # Clear the file
        print("✅ Log file cleared successfully.")
    except Exception as e:
        print(f"❌ Error clearing log file: {e}")

def main():
    """Main function with command line options."""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "clear":
            clear_logs()
        elif command == "all":
            view_logs(lines=1000)  # Show more lines
        elif command.isdigit():
            view_logs(lines=int(command))
        else:
            print("Usage:")
            print("  python view_logs.py        # View last 50 lines")
            print("  python view_logs.py 100    # View last 100 lines")
            print("  python view_logs.py all    # View all lines")
            print("  python view_logs.py clear  # Clear log file")
    else:
        view_logs()  # Default: show last 50 lines

if __name__ == "__main__":
    main()