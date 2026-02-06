#!/bin/bash
# Start both Kalshi and PM copy bots for overnight trading

PROJECT_DIR="/home/mck/Desktop/projects/pm-copy-trading-bot"
cd "$PROJECT_DIR"

# Kill any existing bots
echo "Stopping any existing bots..."
pkill -f "run_kalshi_copy.py" 2>/dev/null
pkill -f "run_pm_copy.py" 2>/dev/null
sleep 2

# Start Kalshi bot in screen
echo "Starting Kalshi Copy Bot..."
screen -dmS kalshi-bot bash -c 'cd /home/mck/Desktop/projects/pm-copy-trading-bot && python3 run_kalshi_copy.py --live 2>&1 | tee -a logs/kalshi_$(date +%Y%m%d).log'
sleep 2

# Start PM bot in screen (dry run mode for safety)
echo "Starting PM Copy Bot (DRY RUN)..."
screen -dmS pm-bot bash -c 'cd /home/mck/Desktop/projects/pm-copy-trading-bot && PM_DRY_RUN=true python3 run_pm_copy.py 2>&1 | tee -a logs/pm_$(date +%Y%m%d).log'
sleep 2

echo ""
echo "✅ Both bots started!"
echo ""
echo "Screen sessions:"
screen -ls | grep -E "kalshi|pm-"
echo ""
echo "To attach:"
echo "  screen -r kalshi-bot    # Kalshi bot"
echo "  screen -r pm-bot        # PM bot"
echo ""
echo "To detach: Ctrl+A D"
echo ""
echo "Logs:"
echo "  tail -f logs/kalshi_$(date +%Y%m%d).log"
echo "  tail -f logs/pm_$(date +%Y%m%d).log"
