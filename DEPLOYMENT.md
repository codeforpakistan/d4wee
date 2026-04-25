# Deployment Guide for D4Wee Dashboard

This guide will help you deploy the Google Classroom Dashboard to your bare metal server at `178.128.126.118`.

## Server Details
- **Server**: root@178.128.126.118
- **Deploy Path**: /root/d4wee
- **Domain**: d4wee.codeforpakistan.org
- **Reverse Proxy**: Caddy
- **Application Server**: Gunicorn

## Prerequisites on Server

### 1. Install System Dependencies

SSH into your server:
```bash
ssh root@178.128.126.118
```

Install required packages:
```bash
# Update system
apt update && apt upgrade -y

# Install Python and dependencies
apt install -y python3 python3-pip python3-venv

# Install Caddy
apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update
apt install -y caddy
```

## Initial Server Setup

### 2. Setup Caddy Configuration

```bash
# Copy Caddyfile to Caddy config directory
cp /root/d4wee/Caddyfile /etc/caddy/Caddyfile

# Create log directory
mkdir -p /var/log/caddy

# Restart Caddy
systemctl restart caddy
systemctl enable caddy
```

### 3. Setup Systemd Service

```bash
# Copy service file
cp /root/d4wee/d4wee.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable and start service
systemctl enable d4wee
systemctl start d4wee

# Check status
systemctl status d4wee
```

### 4. Configure Environment Variables

```bash
cd /root/d4wee

# Copy and edit production environment file
cp .env.production .env

# Edit with your actual values
nano .env
```

Update the following values in `.env`:
- `SECRET_KEY`: Generate a new secret key (use `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`)
- `SOCIALACCOUNT_PROVIDERS_GOOGLE_CLIENT_ID`: Your Google OAuth Client ID
- `SOCIALACCOUNT_PROVIDERS_GOOGLE_CLIENT_SECRET`: Your Google OAuth Client Secret

### 5. Update Google Cloud Console

Add your production domain to Google OAuth authorized redirect URIs:
1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Select your OAuth 2.0 Client ID
3. Add to **Authorized redirect URIs**:
   ```
   https://d4wee.codeforpakistan.org/accounts/google/login/callback/
   ```
4. Save and wait 1-2 minutes for changes to propagate

## Deployment

### Option 1: Automated Deployment (from your local machine)

Make the deploy script executable:
```bash
chmod +x deploy.sh
```

Run deployment:
```bash
./deploy.sh
```

### Option 2: Manual Deployment

1. **Sync files to server:**
```bash
rsync -avz --progress \
    --exclude='.venv/' \
    --exclude='db.sqlite3' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='staticfiles/' \
    ./ root@178.128.126.118:/root/d4wee/
```

2. **SSH into server and setup:**
```bash
ssh root@178.128.126.118
cd /root/d4wee

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic --noinput

# Restart service
systemctl restart d4wee
```

## Useful Commands

### Check Application Status
```bash
# Service status
systemctl status d4wee

# View logs
journalctl -u d4wee -f

# Application logs
tail -f /var/log/d4wee/access.log
tail -f /var/log/d4wee/error.log
```

### Check Caddy Status
```bash
# Service status
systemctl status caddy

# View logs
journalctl -u caddy -f

# Test configuration
caddy validate --config /etc/caddy/Caddyfile
```

### Restart Services
```bash
# Restart Django application
systemctl restart d4wee

# Restart Caddy
systemctl restart caddy

# Reload without downtime
systemctl reload d4wee
```

### Database Management
```bash
cd /root/d4wee
source .venv/bin/activate

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Access Django shell
python manage.py shell
```

## Troubleshooting

### Application won't start
1. Check logs: `journalctl -u d4wee -f`
2. Verify .env file exists and has correct values
3. Ensure virtual environment is created: `ls -la /root/d4wee/.venv`
4. Check port 8000 is not in use: `lsof -i :8000`

### 502 Bad Gateway
1. Check if gunicorn is running: `systemctl status d4wee`
2. Verify Caddy can reach localhost:8000
3. Check firewall rules: `ufw status`

### Static files not loading
1. Run `python manage.py collectstatic --noinput`
2. Restart service: `systemctl restart d4wee`
3. Check Caddy configuration for `/static/*` handler

### Domain not resolving
1. Verify DNS points to 178.128.126.118
2. Check Caddy logs: `journalctl -u caddy -f`
3. Test with curl: `curl -I https://d4wee.codeforpakistan.org`

## Security Recommendations

1. **Setup Firewall:**
```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

2. **Regular Updates:**
```bash
apt update && apt upgrade -y
```

3. **Backup Database:**
```bash
# Backup SQLite
cp /root/d4wee/db.sqlite3 /root/backups/db.sqlite3.$(date +%Y%m%d)
```

4. **Monitor Logs:**
Set up log rotation for application logs in `/var/log/d4wee/`

## Next Steps

1. Test the deployment: https://d4wee.codeforpakistan.org
2. Sign in with Google to verify OAuth works
3. Sync classroom data: `python manage.py sync_classroom`
4. Setup automated backups
5. Configure monitoring (optional)
