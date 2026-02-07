#!/bin/bash
# Start trading bots with proper logging

cd /home/mck/Desktop/projects/pm-copy-trading-bot

# Kill existing
pkill -f "run_kalshi_copy\|run_pm_copy" 2>/dev/null
sleep 2

# Start Kalshi
nohup python3 run_kalshi_copy.py --live > logs/kalshi_$(date +%Y%m%d_%H%M%S).log 2>&1 &
echo "Kalshi: $!"

# Start PM (with limits)
export PM_DRY_RUN=false
export PM_MAX_POSITION_SIZE=2.0
export PM_MAX_TOTAL_EXPOSURE=10.0
nohup python3 run_pm_copy.py > logs/pm_$(date +%Y%m%d_%H%M%S).log 2>&1 &
echo "PM: $!"

echo ""
echo "Bots started! Watch logs:"
echo "  tail -f logs/kalshi_*.log"
echo "  tail -f logs/pm_*.log"
