#!/bin/bash

# cit.is Deployment Script
# Manages Gunicorn, Redis, and Celery services

set -e

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="${PROJECT_DIR}/pids"
LOG_DIR="${PROJECT_DIR}/logs"

# Service configuration
GUNICORN_HOST="127.0.0.1"
GUNICORN_PORT="8998"
GUNICORN_WORKERS="10"
REDIS_PORT="6379"

# Create directories
mkdir -p "${PID_DIR}" "${LOG_DIR}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"; }
error() { echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"; }

# Murder function for killing processes on ports
murder() {
    local port=$1
    if [ -z "$port" ]; then
        error "Usage: murder <port>"
        return 1
    fi
    
    log "Killing processes on port $port"
    
    # Find and kill processes using the port
    local pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        for pid in $pids; do
            log "Killing PID $pid on port $port"
            kill -9 $pid 2>/dev/null || true
        done
    else
        log "No processes found on port $port"
    fi
}

# Check if process is running
is_running() {
    local pidfile=$1
    if [ -f "$pidfile" ]; then
        local pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            return 0
        else
            rm -f "$pidfile"
            return 1
        fi
    fi
    return 1
}

# Start Redis
start_redis() {
    local pidfile="${PID_DIR}/redis.pid"
    local logfile="${LOG_DIR}/redis.log"
    
    if is_running "$pidfile"; then
        warn "Redis is already running (PID: $(cat $pidfile))"
        return 0
    fi
    
    # Check if Redis is already running on system
    if redis-cli -p $REDIS_PORT ping >/dev/null 2>&1; then
        log "Redis is already running on system"
        return 0
    fi
    
    log "Starting Redis server..."
    redis-server --daemonize yes \
                 --port $REDIS_PORT \
                 --pidfile "$pidfile" \
                 --logfile "$logfile" \
                 --dir "${PROJECT_DIR}" \
                 --save 900 1 \
                 --save 300 10 \
                 --save 60 10000
    
    # Wait for Redis to start
    sleep 2
    if redis-cli -p $REDIS_PORT ping >/dev/null 2>&1; then
        log "Redis started successfully"
    else
        error "Failed to start Redis"
        return 1
    fi
}

# Stop Redis
stop_redis() {
    local pidfile="${PID_DIR}/redis.pid"
    
    if is_running "$pidfile"; then
        local pid=$(cat "$pidfile")
        log "Stopping Redis (PID: $pid)..."
        kill "$pid"
        
        # Wait for shutdown
        local count=0
        while kill -0 "$pid" 2>/dev/null && [ $count -lt 10 ]; do
            sleep 1
            count=$((count + 1))
        done
        
        if kill -0 "$pid" 2>/dev/null; then
            warn "Redis didn't stop gracefully, force killing..."
            kill -9 "$pid"
        fi
        
        rm -f "$pidfile"
        log "Redis stopped"
    else
        # Try to stop Docker or system Redis if it's running
        if docker exec redis redis-cli ping >/dev/null 2>&1; then
            log "Stopping Docker Redis..."
            docker stop redis
        elif redis-cli -p $REDIS_PORT ping >/dev/null 2>&1; then
            log "Stopping system Redis..."
            redis-cli -p $REDIS_PORT shutdown
        else
            warn "Redis is not running"
        fi
    fi
}

# Start Gunicorn
start_gunicorn() {
    local pidfile="${PID_DIR}/gunicorn.pid"
    local logfile="${LOG_DIR}/gunicorn.log"
    local access_log="${LOG_DIR}/gunicorn_access.log"
    
    if is_running "$pidfile"; then
        warn "Gunicorn is already running (PID: $(cat $pidfile))"
        return 0
    fi
    
    # Kill any existing processes on the port
    murder $GUNICORN_PORT
    
    log "Starting Gunicorn server..."
    cd "$PROJECT_DIR"
    
    gunicorn citis.wsgi:application \
        --bind "${GUNICORN_HOST}:${GUNICORN_PORT}" \
        --workers $GUNICORN_WORKERS \
        --daemon \
        --pid "$pidfile" \
        --log-file "$logfile" \
        --access-logfile "$access_log" \
        --log-level info \
        --worker-class sync \
        --worker-connections 1000 \
        --max-requests 1000 \
        --max-requests-jitter 50 \
        --timeout 60 \
        --keep-alive 2
    
    # Wait for Gunicorn to start
    sleep 3
    if is_running "$pidfile"; then
        log "Gunicorn started successfully on http://${GUNICORN_HOST}:${GUNICORN_PORT}"
    else
        error "Failed to start Gunicorn"
        return 1
    fi
}

# Stop Gunicorn
stop_gunicorn() {
    local pidfile="${PID_DIR}/gunicorn.pid"
    
    if is_running "$pidfile"; then
        local pid=$(cat "$pidfile")
        log "Stopping Gunicorn (PID: $pid)..."
        kill -TERM "$pid"
        
        # Wait for graceful shutdown
        local count=0
        while kill -0 "$pid" 2>/dev/null && [ $count -lt 15 ]; do
            sleep 1
            count=$((count + 1))
        done
        
        if kill -0 "$pid" 2>/dev/null; then
            warn "Gunicorn didn't stop gracefully, force killing..."
            kill -9 "$pid"
        fi
        
        rm -f "$pidfile"
        log "Gunicorn stopped"
    else
        warn "Gunicorn is not running"
        # Kill any processes on the port anyway
        murder $GUNICORN_PORT
    fi
}

# Start Celery Worker
start_celery() {
    local pidfile="${PID_DIR}/celery.pid"
    local logfile="${LOG_DIR}/celery.log"
    
    if is_running "$pidfile"; then
        warn "Celery worker is already running (PID: $(cat $pidfile))"
        return 0
    fi
    
    log "Starting Celery worker..."
    cd "$PROJECT_DIR"
    
    celery -A citis worker \
        --detach \
        --pidfile="$pidfile" \
        --logfile="$logfile" \
        --loglevel=info \
        --concurrency=4 \
        --max-tasks-per-child=1000 \
        --time-limit=300 \
        --soft-time-limit=240 \
        --queues=archive,assets,analytics,celery
    
    # Wait for Celery to start
    sleep 3
    if is_running "$pidfile"; then
        log "Celery worker started successfully"
    else
        error "Failed to start Celery worker"
        return 1
    fi
}

# Stop Celery Worker
stop_celery() {
    local pidfile="${PID_DIR}/celery.pid"
    
    if is_running "$pidfile"; then
        local pid=$(cat "$pidfile")
        log "Stopping Celery worker (PID: $pid)..."
        
        # Send TERM signal for graceful shutdown
        kill -TERM "$pid"
        
        # Wait for graceful shutdown
        local count=0
        while kill -0 "$pid" 2>/dev/null && [ $count -lt 30 ]; do
            sleep 1
            count=$((count + 1))
        done
        
        if kill -0 "$pid" 2>/dev/null; then
            warn "Celery didn't stop gracefully, force killing..."
            kill -9 "$pid"
        fi
        
        rm -f "$pidfile"
        log "Celery worker stopped"
    else
        warn "Celery worker is not running"
    fi
    
    # Kill any remaining celery processes
    pkill -f "celery.*citis" 2>/dev/null || true
}

# Start Celery Beat (optional)
start_beat() {
    local pidfile="${PID_DIR}/celery-beat.pid"
    local logfile="${LOG_DIR}/celery-beat.log"
    
    if is_running "$pidfile"; then
        warn "Celery beat is already running (PID: $(cat $pidfile))"
        return 0
    fi
    
    log "Starting Celery beat scheduler..."
    cd "$PROJECT_DIR"
    
    celery -A citis beat \
        --detach \
        --pidfile="$pidfile" \
        --logfile="$logfile" \
        --loglevel=info \
        --scheduler=django_celery_beat.schedulers:DatabaseScheduler
    
    sleep 3
    if is_running "$pidfile"; then
        log "Celery beat started successfully"
    else
        error "Failed to start Celery beat"
        return 1
    fi
}

# Stop Celery Beat
stop_beat() {
    local pidfile="${PID_DIR}/celery-beat.pid"
    
    if is_running "$pidfile"; then
        local pid=$(cat "$pidfile")
        log "Stopping Celery beat (PID: $pid)..."
        kill -TERM "$pid"
        
        local count=0
        while kill -0 "$pid" 2>/dev/null && [ $count -lt 10 ]; do
            sleep 1
            count=$((count + 1))
        done
        
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid"
        fi
        
        rm -f "$pidfile"
        log "Celery beat stopped"
    else
        warn "Celery beat is not running"
    fi
}

# Status check
status() {
    echo -e "\n${BLUE}=== cit.is Service Status ===${NC}"
    
    # Redis (Docker)
    if docker exec redis redis-cli ping >/dev/null 2>&1; then
        echo -e "Redis:          ${GREEN}✓ Running${NC} (Docker)"
    elif redis-cli -p $REDIS_PORT ping >/dev/null 2>&1; then
        echo -e "Redis:          ${GREEN}✓ Running${NC} (System)"
    else
        echo -e "Redis:          ${RED}✗ Stopped${NC} (Start with: docker start redis)"
    fi
    
    # Gunicorn
    local gunicorn_pidfile="${PID_DIR}/gunicorn.pid"
    if is_running "$gunicorn_pidfile"; then
        echo -e "Gunicorn:       ${GREEN}✓ Running${NC} (PID: $(cat $gunicorn_pidfile))"
        echo -e "URL:            ${BLUE}http://${GUNICORN_HOST}:${GUNICORN_PORT}${NC}"
    else
        echo -e "Gunicorn:       ${RED}✗ Stopped${NC}"
    fi
    
    # Celery Worker
    local celery_pidfile="${PID_DIR}/celery.pid"
    if is_running "$celery_pidfile"; then
        echo -e "Celery Worker:  ${GREEN}✓ Running${NC} (PID: $(cat $celery_pidfile))"
    else
        echo -e "Celery Worker:  ${RED}✗ Stopped${NC}"
    fi
    
    # Celery Beat
    local beat_pidfile="${PID_DIR}/celery-beat.pid"
    if is_running "$beat_pidfile"; then
        echo -e "Celery Beat:    ${GREEN}✓ Running${NC} (PID: $(cat $beat_pidfile))"
    else
        echo -e "Celery Beat:    ${YELLOW}⚬ Stopped${NC} (optional)"
    fi
    
    echo ""
}

# Start all services
start_all() {
    log "Starting all cit.is services..."
    
    # Check if Redis is already running (via Docker or system)
    if docker exec redis redis-cli ping >/dev/null 2>&1; then
        log "Redis is already running (Docker container)"
    elif redis-cli -p $REDIS_PORT ping >/dev/null 2>&1; then
        log "Redis is already running (system service)"
    else
        warn "Redis is not running! Start it manually with: docker start redis"
        return 1
    fi
    
    start_gunicorn
    start_celery
    status
}

# Stop all services
stop_all() {
    log "Stopping all cit.is services..."
    stop_beat
    stop_celery
    stop_gunicorn
    
    # Note: Redis is managed by Docker, not stopping it
    log "Note: Redis (Docker) left running - stop manually if needed: docker stop redis"
    
    # Clean up any remaining processes
    murder $GUNICORN_PORT
    
    log "All services stopped"
}

# Restart all services
restart_all() {
    log "Restarting all cit.is services..."
    stop_all
    sleep 2
    start_all
}

# Show logs
logs() {
    local service=${1:-"all"}
    case $service in
        "gunicorn")
            tail -f "${LOG_DIR}/gunicorn.log"
            ;;
        "celery")
            tail -f "${LOG_DIR}/celery.log"
            ;;
        "all")
            tail -f "${LOG_DIR}"/*.log
            ;;
        *)
            error "Unknown service: $service"
            echo "Available services: gunicorn, celery, all"
            echo "For Redis logs: docker logs redis"
            ;;
    esac
}

# Show usage
usage() {
    echo "cit.is Deployment Script"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start           Start all services (redis, gunicorn, celery)"
    echo "  stop            Stop all services"
    echo "  restart         Restart all services"
    echo "  status          Show service status"
    echo "  logs [SERVICE]  Show logs (gunicorn|celery|all)"
    echo ""
    echo "Individual service commands:"
    echo "  start-web       Start Gunicorn web server"
    echo "  stop-web        Stop Gunicorn web server"
    echo "  start-celery    Start Celery worker"
    echo "  stop-celery     Stop Celery worker"
    echo "  start-beat      Start Celery beat scheduler"
    echo "  stop-beat       Stop Celery beat scheduler"
    echo ""
    echo "Docker Redis commands:"
    echo "  docker start redis    Start Redis container"
    echo "  docker stop redis     Stop Redis container"
    echo ""
    echo "Utility commands:"
    echo "  murder PORT     Kill all processes on specified port"
    echo ""
    echo "Configuration:"
    echo "  Host: $GUNICORN_HOST"
    echo "  Port: $GUNICORN_PORT"
    echo "  Workers: $GUNICORN_WORKERS"
}

# Main command handling
case "${1:-}" in
    "start")
        start_all
        ;;
    "stop")
        stop_all
        ;;
    "restart")
        restart_all
        ;;
    "status")
        status
        ;;
    "logs")
        logs "${2:-all}"
        ;;
    "start-web")
        start_gunicorn
        ;;
    "stop-web")
        stop_gunicorn
        ;;
    "start-celery")
        start_celery
        ;;
    "stop-celery")
        stop_celery
        ;;
    "start-beat")
        start_beat
        ;;
    "stop-beat")
        stop_beat
        ;;
    "murder")
        if [ -n "${2:-}" ]; then
            murder "$2"
        else
            error "Port number required"
            echo "Usage: $0 murder <port>"
            exit 1
        fi
        ;;
    ""|"-h"|"--help"|"help")
        usage
        ;;
    *)
        error "Unknown command: $1"
        usage
        exit 1
        ;;
esac