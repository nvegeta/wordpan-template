#!/bin/bash
set -e

echo "Downloading required files..."

# Use the agent's download-files command (handles caching internally)
uv run src/agent.py download-files

echo "Ready to start"

# Execute the main command
exec "$@"

