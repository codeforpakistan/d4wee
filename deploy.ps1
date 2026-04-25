# Deployment script for D4Wee Dashboard (PowerShell)
# Run this from your local Windows machine

$SERVER = "root@178.128.126.118"
$DEPLOY_PATH = "/root/d4wee"

Write-Host "🚀 Starting deployment to $SERVER..." -ForegroundColor Green

# Step 1: Sync files to server using rsync (requires WSL or rsync for Windows)
Write-Host "📦 Syncing files to server..." -ForegroundColor Yellow

$excludeArgs = @(
    "--exclude=.venv/",
    "--exclude=db.sqlite3",
    "--exclude=__pycache__/",
    "--exclude=*.pyc",
    "--exclude=.git/",
    "--exclude=staticfiles/",
    "--exclude=*.log",
    "--exclude=node_modules/",
    "--exclude=.env"
)

# Try to use WSL rsync if available, otherwise use scp
try {
    wsl rsync -avz --progress $excludeArgs ./ "${SERVER}:${DEPLOY_PATH}/"
} catch {
    Write-Host "⚠️  WSL rsync not available. Please use deploy.sh from WSL or Git Bash" -ForegroundColor Red
    Write-Host "Alternative: Manually copy files using WinSCP or similar tool" -ForegroundColor Yellow
    exit 1
}

# Step 2: Run deployment commands on server
Write-Host "⚙️  Running deployment commands on server..." -ForegroundColor Yellow

$commands = @"
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

# Install whitenoise if not already in requirements
pip install whitenoise

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Restart the service
sudo systemctl restart d4wee

echo "✅ Deployment completed!"
"@

ssh $SERVER $commands

Write-Host "🎉 Deployment finished successfully!" -ForegroundColor Green
Write-Host "Visit: https://d4wee.codeforpakistan.org" -ForegroundColor Cyan
