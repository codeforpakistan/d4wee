#!/bin/bash
# Deployment script for D4Wee Dashboard

set -e

SERVER="root@178.128.126.118"
DEPLOY_PATH="/root/d4wee"

echo "🚀 Starting deployment to $SERVER..."

# Step 1: Sync files to server (excluding unnecessary files)
echo "📦 Syncing files to server..."
rsync -avz --progress \
    --exclude='.venv/' \
    --exclude='db.sqlite3' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='staticfiles/' \
    --exclude='*.log' \
    --exclude='node_modules/' \
    --exclude='.env' \
    ./ $SERVER:$DEPLOY_PATH/

# Step 2: Run deployment commands on server
echo "⚙️  Running deployment commands on server..."
ssh $SERVER << 'ENDSSH'
cd /root/d4wee

# Create log directory
mkdir -p /var/log/d4wee

# Install Python dependencies
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Restart the service
sudo systemctl restart d4wee

echo "✅ Deployment completed!"
ENDSSH

echo "🎉 Deployment finished successfully!"
