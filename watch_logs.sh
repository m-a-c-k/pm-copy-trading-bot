#!/bin/bash
# Watch bot logs

cd /home/mck/Desktop/projects/pm-copy-trading-bot

echo "Tailing latest logs..."
echo "Ctrl+C to stop"
echo ""

# Get latest logs
KALSHI_LOG=$(ls -t logs/kalshi_*.log 2>/dev/null | head -1)
PM_LOG=$(ls -t logs/pm_*.log 2>/dev/null | head -1)

if [ -n "$KALSHI_LOG" ]; then
    echo "Kalshi: $KALSHI_LOG"
    tail -f "$KALSHI_LOG" &
    KALSHI_PID=$!
fi

if [ -n "$PM_LOG" ]; then
    echo "PM: $PM_LOG"
    tail -f "$PM_LOG" &
    PM_PID=$!
fi

# Wait for interrupt
trap "kill $KALSHI_PID $PM_PID 2>/dev/null; exit" INT
wait
