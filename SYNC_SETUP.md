# D4Wee Sync Setup Instructions

## Automated Nightly Sync

The sync management command is configured to run every night at 2:00 AM using systemd timers.

### Installation Steps

1. **Copy the service and timer files to systemd directory:**
   ```bash
   sudo cp d4wee-sync.service /etc/systemd/system/
   sudo cp d4wee-sync.timer /etc/systemd/system/
   ```

2. **Reload systemd to recognize the new files:**
   ```bash
   sudo systemctl daemon-reload
   ```

3. **Enable and start the timer:**
   ```bash
   sudo systemctl enable d4wee-sync.timer
   sudo systemctl start d4wee-sync.timer
   ```

4. **Verify the timer is active:**
   ```bash
   sudo systemctl status d4wee-sync.timer
   sudo systemctl list-timers d4wee-sync.timer
   ```

### Management Commands

- **Check timer status:**
  ```bash
  sudo systemctl status d4wee-sync.timer
  ```

- **View next scheduled run:**
  ```bash
  sudo systemctl list-timers d4wee-sync.timer
  ```

- **View sync logs:**
  ```bash
  sudo journalctl -u d4wee-sync.service -f
  ```

- **View recent sync runs:**
  ```bash
  sudo journalctl -u d4wee-sync.service --since today
  ```

- **Run sync manually (for testing):**
  ```bash
  sudo systemctl start d4wee-sync.service
  ```

- **Stop the timer:**
  ```bash
  sudo systemctl stop d4wee-sync.timer
  ```

- **Disable automatic sync:**
  ```bash
  sudo systemctl disable d4wee-sync.timer
  ```

### Configuration Details

- **Schedule:** Every night at 2:00 AM
- **Randomized delay:** 0-15 minutes to avoid load spikes
- **Persistent:** If a scheduled run is missed (e.g., server was off), it will run when the system starts
- **Logging:** All output is captured in systemd journal

### Troubleshooting

If the sync fails:

1. Check service logs:
   ```bash
   sudo journalctl -u d4wee-sync.service -n 50
   ```

2. Test the command manually:
   ```bash
   cd /root/d4wee
   source .venv/bin/activate
   python manage.py sync
   ```

3. Verify the service can run:
   ```bash
   sudo systemctl start d4wee-sync.service
   sudo systemctl status d4wee-sync.service
   ```

### Changing the Schedule

To run at a different time, edit `/etc/systemd/system/d4wee-sync.timer` and change the `OnCalendar` line:

- Daily at 3:00 AM: `OnCalendar=*-*-* 03:00:00`
- Every 6 hours: `OnCalendar=*-*-* 00,06,12,18:00:00`
- Weekly on Sunday at 2:00 AM: `OnCalendar=Sun *-*-* 02:00:00`

After editing, reload systemd:
```bash
sudo systemctl daemon-reload
sudo systemctl restart d4wee-sync.timer
```
