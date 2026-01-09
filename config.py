
---

## **FILE 6: `config.py`** (Configuration File)

```python
# Instagram Bot Configuration
# ===========================
# IMPORTANT: Replace these values with your own!

# Telegram Bot Token from @BotFather
# Format: "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Your Telegram User ID (get from @userinfobot)
# Must be a string, e.g., "6107382622"
ADMIN_ID = "YOUR_USER_ID_HERE"

# Bot Settings
# ============
# Default free trial days for new users
FREE_TRIAL_DAYS = 30

# Spam settings
DEFAULT_DELAY_MIN = 2  # seconds
DEFAULT_DELAY_MAX = 5  # seconds
DEFAULT_MESSAGE_COUNT = 100

# Auto-restart settings
AUTO_RESTART = True
RESTART_DELAY = 10  # seconds between restart attempts

# Logging settings
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_TO_FILE = True
LOG_TO_CONSOLE = True

# Data files
DATA_DIR = "instagram_bot_data"
MESSAGES_FILE = "messages.json"
SESSIONS_FILE = "sessions.json"
USERS_FILE = "users_data.json"

# Instagram API settings (if needed)
INSTAGRAM_TIMEOUT = 30
MAX_SESSIONS = 20

# Payment settings (for future use)
CURRENCY = "USD"
PAYMENT_METHODS = ["PayPal", "Crypto", "Bank Transfer"]

# Broadcast settings
BROADCAST_DELAY = 0.1  # seconds between sending broadcast messages
MAX_BROADCAST_USERS = 1000

# Security settings
MAX_LOGIN_ATTEMPTS = 3
SESSION_TIMEOUT = 3600  # 1 hour in seconds

# Feature flags
ENABLE_ADMIN_PANEL = True
ENABLE_BROADCAST = True
ENABLE_USER_MANAGEMENT = True
ENABLE_SPAM = True
ENABLE_SESSIONS = True

# Don't edit below this line unless you know what you're doing
# ============================================================
import os
from pathlib import Path

# Create data directory if it doesn't exist
DATA_PATH = Path(DATA_DIR)
DATA_PATH.mkdir(exist_ok=True)

# Logs directory
LOGS_DIR = Path("bot_logs")
LOGS_DIR.mkdir(exist_ok=True)

# Validate configuration
def validate_config():
    """Validate the configuration"""
    errors = []
    
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        errors.append("BOT_TOKEN not set. Get it from @BotFather")
    
    if ADMIN_ID == "YOUR_USER_ID_HERE":
        errors.append("ADMIN_ID not set. Get it from @userinfobot")
    
    if not ADMIN_ID.isdigit():
        errors.append("ADMIN_ID must be numeric")
    
    if FREE_TRIAL_DAYS < 0:
        errors.append("FREE_TRIAL_DAYS must be positive")
    
    if DEFAULT_DELAY_MIN <= 0 or DEFAULT_DELAY_MAX <= 0:
        errors.append("Delay values must be positive")
    
    if DEFAULT_DELAY_MIN > DEFAULT_DELAY_MAX:
        errors.append("DEFAULT_DELAY_MIN must be less than DEFAULT_DELAY_MAX")
    
    if DEFAULT_MESSAGE_COUNT <= 0:
        errors.append("DEFAULT_MESSAGE_COUNT must be positive")
    
    return errors

# Check configuration on import
config_errors = validate_config()
if config_errors:
    print("⚠️ Configuration errors found:")
    for error in config_errors:
        print(f"  - {error}")
    print("\nPlease edit config.py with correct values!")
