# D4Wee Deployment Guide

## Initial Deployment

### 1. Collect Static Files

Before Caddy can serve static files, Django needs to collect them:

```bash
cd /root/d4wee
source .venv/bin/activate
python manage.py collectstatic --noinput
```

This creates/updates the `staticfiles` directory with all CSS, JavaScript, and other static assets.

### 2. Update Caddy Configuration

Copy the updated Caddyfile to apply static file serving:

```bash
sudo cp /root/d4wee/Caddyfile /etc/caddy/Caddyfile
sudo systemctl reload caddy
```

Verify Caddy configuration is valid:

```bash
sudo caddy validate --config /etc/caddy/Caddyfile
```

### 3. Install Systemd Timer for Sync

Set up the automated nightly sync (see SYNC_SETUP.md for details):

```bash
sudo cp d4wee-sync.service d4wee-sync.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable d4wee-sync.timer
sudo systemctl start d4wee-sync.timer
```

## After Code Updates

When you deploy new code changes:

```bash
cd /root/d4wee

# 1. Pull latest code
git pull

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Install/update dependencies
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate

# 5. Collect static files (important!)
python manage.py collectstatic --noinput

# 6. Restart the Django service
sudo systemctl restart d4wee.service

# 7. Check service status
sudo systemctl status d4wee.service
```

## Verify Static Files are Served by Caddy

Test that static files are being served correctly:

```bash
# Check a static file (replace with actual static file path)
curl -I https://d4wee.codeforpakistan.org/static/admin/css/base.css

# You should see:
# - HTTP 200 status
# - Cache-Control header with long max-age
# - server: Caddy
```

## Service Management

### Django Application

```bash
# Start
sudo systemctl start d4wee.service

# Stop
sudo systemctl stop d4wee.service

# Restart
sudo systemctl restart d4wee.service

# Status
sudo systemctl status d4wee.service

# View logs
sudo journalctl -u d4wee.service -f
```

### Caddy Web Server

```bash
# Start
sudo systemctl start caddy

# Stop
sudo systemctl stop caddy

# Reload (apply config changes without downtime)
sudo systemctl reload caddy

# Status
sudo systemctl status caddy

# View logs
sudo journalctl -u caddy -f

# View access logs
sudo tail -f /var/log/caddy/d4wee.log
```

### Nightly Sync Timer

See [SYNC_SETUP.md](SYNC_SETUP.md) for complete sync management instructions.

## File Locations

- **Application:** `/root/d4wee/`
- **Virtual Environment:** `/root/d4wee/.venv/`
- **Static Files:** `/root/d4wee/staticfiles/`
- **Media Files:** `/root/d4wee/media/`
- **Database:** `/root/d4wee/db.sqlite3` (or PostgreSQL)
- **Caddy Config:** `/etc/caddy/Caddyfile`
- **Systemd Services:** `/etc/systemd/system/`
- **Application Logs:** `/var/log/d4wee/`
- **Caddy Logs:** `/var/log/caddy/`

## Troubleshooting

### Static Files Not Loading

1. Verify files were collected:
   ```bash
   ls -la /root/d4wee/staticfiles/
   ```

2. Check Caddy is serving them:
   ```bash
   curl -I https://d4wee.codeforpakistan.org/static/admin/css/base.css
   ```

3. Check Caddy logs:
   ```bash
   sudo journalctl -u caddy -n 50
   ```

### Application Not Responding

1. Check if Gunicorn is running:
   ```bash
   sudo systemctl status d4wee.service
   ```

2. Check application logs:
   ```bash
   sudo tail -f /var/log/d4wee/error.log
   ```

3. Test manually:
   ```bash
   curl http://localhost:8000
   ```

### Sync Not Running

See the troubleshooting section in [SYNC_SETUP.md](SYNC_SETUP.md).

## Security Checklist

- [ ] `DEBUG = False` in production
- [ ] Strong `SECRET_KEY` set in environment
- [ ] `ALLOWED_HOSTS` properly configured
- [ ] Database credentials secured
- [ ] Google OAuth credentials secured
- [ ] HTTPS enabled (Caddy handles this automatically)
- [ ] Static files served with proper cache headers
- [ ] Log files rotated (configure logrotate)

## Performance Tips

1. **Static Files:** Caddy serves these directly with aggressive caching
2. **Database:** Consider migrating to PostgreSQL for better performance
3. **Gunicorn Workers:** Adjust `--workers` based on CPU cores (current: 3)
4. **Caching:** Consider adding Redis for Django caching
5. **Monitoring:** Set up uptime monitoring and alerts
