#!/bin/bash
# cognee MCP server setup script
# Usage: ./cognee-setup.sh [start|stop|status]

COGNEE_DIR="/home/user/cognee-mcp-repo/cognee-mcp"
VENV="$COGNEE_DIR/.venv"
PID_FILE="/tmp/cognee-mcp.pid"
ENV_FILE="$COGNEE_DIR/.env"

start() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "cognee MCP server is already running (PID $(cat $PID_FILE))"
        return 0
    fi

    if [ ! -f "$ENV_FILE" ]; then
        echo "WARNING: No .env file found at $ENV_FILE"
        echo "Create one with at minimum: LLM_API_KEY=\"your-key\""
        echo "Starting server anyway (will work for basic operations)..."
    fi

    cd "$COGNEE_DIR"
    source "$VENV/bin/activate"

    # Start in SSE mode for network access (claude code + other clients)
    nohup python src/server.py --transport sse --host 127.0.0.1 --port 8100 \
        > /tmp/cognee-mcp.log 2>&1 &
    echo $! > "$PID_FILE"
    echo "cognee MCP server started on http://127.0.0.1:8100/sse (PID $(cat $PID_FILE))"
    echo "Logs: /tmp/cognee-mcp.log"
}

stop() {
    if [ -f "$PID_FILE" ]; then
        kill "$(cat "$PID_FILE")" 2>/dev/null
        rm -f "$PID_FILE"
        echo "cognee MCP server stopped"
    else
        echo "cognee MCP server is not running"
    fi
}

status() {
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "cognee MCP server is running (PID $(cat $PID_FILE))"
    else
        echo "cognee MCP server is not running"
        rm -f "$PID_FILE" 2>/dev/null
    fi
}

case "${1:-start}" in
    start)  start ;;
    stop)   stop ;;
    status) status ;;
    *)      echo "Usage: $0 {start|stop|status}" ;;
esac
