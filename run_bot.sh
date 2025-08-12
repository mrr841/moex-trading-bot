#!/bin/bash

# --------------------------
# Trading Bot Launch Script
# Version: 1.2.0
# --------------------------

# Strict mode
set -euo pipefail
IFS=$'\n\t'

# Configuration
VENV_DIR="venv"
CONFIG_FILE="config.json"
LOG_DIR="logs"
PYTHON_CMD="python3"
MAIN_SCRIPT="main.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
function activate_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${RED}Error: Virtual environment not found. Run setup first.${NC}"
        exit 1
    fi

    if [[ "$OSTYPE" == "linux-gnu"* || "$OSTYPE" == "darwin"* ]]; then
        source "$VENV_DIR/bin/activate"
    else
        source "$VENV_DIR/Scripts/activate"
    fi
}

function check_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${YELLOW}Warning: Config file not found. Using default settings.${NC}"
        cp config.example.json "$CONFIG_FILE"
    fi
}

function setup_logs() {
    mkdir -p "$LOG_DIR"
    LOG_FILE="$LOG_DIR/bot_$(date +%Y%m%d_%H%M%S).log"
    touch "$LOG_FILE"
}

function start_bot() {
    local mode="${1:-paper}"
    local telegram="${2:-false}"

    echo -e "${GREEN}Starting Trading Bot in $mode mode...${NC}"
    echo -e "Logs: ${YELLOW}$LOG_FILE${NC}"

    local cmd="$PYTHON_CMD $MAIN_SCRIPT --mode=$mode"
    if [ "$telegram" == "true" ]; then
        cmd+=" --telegram"
    fi

    nohup $cmd >> "$LOG_FILE" 2>&1 &
    echo $! > "$LOG_DIR/bot.pid"

    echo -e "${GREEN}Bot started successfully with PID: $(cat $LOG_DIR/bot.pid)${NC}"
}

function stop_bot() {
    if [ -f "$LOG_DIR/bot.pid" ]; then
        local pid=$(cat "$LOG_DIR/bot.pid")
        kill -TERM "$pid" && rm "$LOG_DIR/bot.pid"
        echo -e "${GREEN}Bot stopped successfully (PID: $pid)${NC}"
    else
        echo -e "${YELLOW}No running bot instance found.${NC}"
    fi
}

function show_help() {
    echo -e "${YELLOW}Usage: $0 [command] [options]${NC}"
    echo ""
    echo "Commands:"
    echo "  start [mode] [--telegram]  Start bot (modes: paper, real, test)"
    echo "  stop                      Stop running bot"
    echo "  restart                   Restart bot"
    echo "  status                    Show bot status"
    echo "  setup                     Initial setup"
    echo ""
    echo "Options:"
    echo "  --telegram                Enable Telegram notifications"
}

# Main execution
case "${1:-}" in
    start)
        activate_venv
        check_config
        setup_logs
        start_bot "${2:-paper}" "${3:-false}"
        ;;
    stop)
        stop_bot
        ;;
    restart)
        stop_bot
        activate_venv
        check_config
        setup_logs
        start_bot "${2:-paper}" "${3:-false}"
        ;;
    status)
        if [ -f "$LOG_DIR/bot.pid" ]; then
            echo -e "${GREEN}Bot is running (PID: $(cat $LOG_DIR/bot.pid))${NC}"
        else
            echo -e "${YELLOW}Bot is not running${NC}"
        fi
        ;;
    setup)
        echo -e "${GREEN}Setting up environment...${NC}"
        $PYTHON_CMD -m venv "$VENV_DIR"
        activate_venv
        pip install --upgrade pip
        pip install -r requirements.txt
        cp config.example.json "$CONFIG_FILE" 2>/dev/null || true
        mkdir -p "$LOG_DIR"
        echo -e "${GREEN}Setup completed successfully${NC}"
        ;;
    *)
        show_help
        exit 1
        ;;
esac

exit 0