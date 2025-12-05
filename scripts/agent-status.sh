#!/bin/bash

# Agent Status Checker
# Quick overview of agent activity and project status

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}=== Agent Status Check ===${NC}"
echo ""

# Recent logs
echo -e "${GREEN}📋 Recent Agent Logs:${NC}"
if ls "$PROJECT_ROOT/agent-logs"/*.log 1>/dev/null 2>&1; then
    ls -lt "$PROJECT_ROOT/agent-logs"/*.log | head -5 | awk '{print "  " $9 " (" $6 " " $7 " " $8 ")"}'
else
    echo "  No logs found"
fi
echo ""

# Roadmap status
echo -e "${GREEN}📊 Roadmap Status:${NC}"
if [[ -f "$PROJECT_ROOT/plans/roadmap.md" ]]; then
    grep -E "(Status:|Phase [0-9])" "$PROJECT_ROOT/plans/roadmap.md" | head -10 | sed 's/^/  /'
else
    echo "  Roadmap not found"
fi
echo ""

# Recent commits
echo -e "${GREEN}📝 Recent Commits:${NC}"
cd "$PROJECT_ROOT" && git log --oneline -5 | sed 's/^/  /'
echo ""

# Dev log latest entry
echo -e "${GREEN}📖 Latest Dev Log Entry:${NC}"
if [[ -f "$PROJECT_ROOT/docs/devlog.md" ]]; then
    # Get the last entry (after the last "## " heading)
    tail -30 "$PROJECT_ROOT/docs/devlog.md" | head -15 | sed 's/^/  /'
else
    echo "  Dev log not found"
fi
echo ""

# NATS status
echo -e "${GREEN}🔌 NATS Status:${NC}"
if docker ps 2>/dev/null | grep -q nats; then
    echo "  NATS is running"
    echo "  Monitoring: http://localhost:8222"
else
    echo "  NATS is not running (docker ps | grep nats)"
fi
echo ""

# Git working tree
echo -e "${GREEN}🌳 Git Working Tree:${NC}"
cd "$PROJECT_ROOT"
if [[ -n $(git status --porcelain) ]]; then
    echo -e "  ${YELLOW}Dirty - uncommitted changes:${NC}"
    git status --short | head -10 | sed 's/^/    /'
else
    echo "  Clean - no uncommitted changes"
fi
echo ""

echo -e "${BLUE}=== End Status Check ===${NC}"
