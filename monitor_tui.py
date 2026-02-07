#!/usr/bin/env python3
"""
Bot Monitor - TUI dashboard for both bots
"""

import os
import sys
import time
import curses
import subprocess
from datetime import datetime

LOG_DIR = "/home/mck/Desktop/projects/pm-copy-trading-bot/logs"


def get_latest_log(prefix):
    """Get latest log file."""
    try:
        files = [f for f in os.listdir(LOG_DIR) if f.startswith(prefix)]
        if files:
            files.sort(reverse=True)
            return os.path.join(LOG_DIR, files[0])
    except:
        pass
    return None


def tail_log(log_file, lines=20):
    """Get last N lines from log."""
    try:
        result = subprocess.run(
            ['tail', '-n', str(lines), log_file],
            capture_output=True,
            text=True
        )
        return result.stdout.split('\n')[-lines:]
    except:
        return ["No log data"]


def get_bot_status():
    """Check if bot processes are running."""
    status = {'kalshi': False, 'pm': False}
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        if 'run_kalshi_copy' in result.stdout:
            status['kalshi'] = True
        if 'run_pm_copy' in result.stdout:
            status['pm'] = True
    except:
        pass
    return status


def draw_screen(stdscr):
    """Main TUI display."""
    curses.curs_set(0)  # Hide cursor
    stdscr.nodelay(1)   # Non-blocking input
    
    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # Title
        title = "🤖 BOT MONITOR"
        stdscr.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
        
        # Status
        status = get_bot_status()
        kalshi_status = "🟢 RUNNING" if status['kalshi'] else "🔴 STOPPED"
        pm_status = "🟢 RUNNING" if status['pm'] else "🔴 STOPPED"
        
        stdscr.addstr(2, 2, f"Kalshi: {kalshi_status}")
        stdscr.addstr(2, 30, f"PM: {pm_status}")
        stdscr.addstr(3, 2, f"Updated: {datetime.now().strftime('%H:%M:%S')}")
        
        # Divider
        stdscr.addstr(4, 0, "=" * width)
        
        # Kalshi logs (left side)
        stdscr.addstr(5, 2, "KALSHI LOGS", curses.A_BOLD)
        kalshi_log = get_latest_log("kalshi")
        if kalshi_log:
            lines = tail_log(kalshi_log, 15)
            for i, line in enumerate(lines):
                if 6 + i < height - 3:
                    # Truncate long lines
                    if len(line) > width // 2 - 4:
                        line = line[:width // 2 - 7] + "..."
                    try:
                        stdscr.addstr(6 + i, 2, line[:width // 2 - 4])
                    except:
                        pass
        
        # PM logs (right side)
        mid_col = width // 2
        stdscr.addstr(5, mid_col + 2, "PM LOGS", curses.A_BOLD)
        pm_log = get_latest_log("pm")
        if pm_log:
            lines = tail_log(pm_log, 15)
            for i, line in enumerate(lines):
                if 6 + i < height - 3:
                    if len(line) > width // 2 - 4:
                        line = line[:width // 2 - 7] + "..."
                    try:
                        stdscr.addstr(6 + i, mid_col + 2, line[:width // 2 - 4])
                    except:
                        pass
        
        # Controls
        stdscr.addstr(height - 2, 2, "Controls: [Q]uit | [R]efresh | [K]ill bots")
        
        stdscr.refresh()
        
        # Handle input
        try:
            key = stdscr.getch()
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord('r') or key == ord('R'):
                continue
            elif key == ord('k') or key == ord('K'):
                os.system("pkill -f 'run_kalshi_copy\|run_pm_copy'")
        except:
            pass
        
        time.sleep(2)


if __name__ == "__main__":
    try:
        curses.wrapper(draw_screen)
    except KeyboardInterrupt:
        print("\nMonitor stopped.")
    except Exception as e:
        print(f"Error: {e}")
        print("\nFalling back to simple log tail...")
        os.system("./watch_logs.sh")
