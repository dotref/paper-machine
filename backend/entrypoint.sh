#!/bin/bash
set -e

# Store a hash of the current requirements file
if [ -f /app/requirements/requirements.txt ]; then
    md5sum /app/requirements/requirements.txt > /tmp/requirements.md5
fi

# Function to check for changes in requirements
check_requirements() {
    if [ -f /app/requirements/requirements.txt ]; then
        if ! md5sum -c /tmp/requirements.md5 &>/dev/null; then
            echo "Requirements changed, reinstalling..."
            pip install --no-cache-dir -r /app/requirements/requirements.txt
            md5sum /app/requirements/requirements.txt > /tmp/requirements.md5
        fi
    fi
}

# Run initial check
check_requirements

# Start your application with hot reload
exec uvicorn src.main:app --host 0.0.0.0 --port 5000 --reload &

# Watch for changes in requirements.txt
while true; do
    sleep 5
    check_requirements
done