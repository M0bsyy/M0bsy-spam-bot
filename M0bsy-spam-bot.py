import os
import sys
import json
import random
import time
import threading
import requests
import hashlib
import string
from datetime import datetime, timedelta
from pathlib import Path
import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

# ========== CONFIGURATION ==========
TELEGRAM_BOT_TOKEN = "8595686704:AAGZ6-f7cjiaET1J2yXM-QBuJCq_fyOMJ7o"
ADMIN_USER_ID = 6107382622  # YOUR TELEGRAM USER ID
BOT_USERNAME = "@M0bsy_spam_bot"
CONTACT_USERNAME = "@M0bsy_olds"

# Initialize bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# ========== INSTAGRAM API - UPDATED WORKING VERSION ==========
def generate_random_string(length=32):
    """Generate random string for CSRF token"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def validate_instagram_session(session_id):
    """Validate Instagram session with better checking"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'accept-language': 'en-US,en;q=0.5',
            'accept-encoding': 'gzip, deflate, br',
            'connection': 'keep-alive',
        }
        
        response = requests.get(
            'https://www.instagram.com/api/v1/users/web_profile_info/?username=instagram',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('data', {}).get('user'):
                    username = data['data']['user'].get('username', 'instagram_user')
                    return True, username, "✅ Valid session"
            except:
                pass
        
        # Try alternative check
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        response = requests.get(
            'https://www.instagram.com/accounts/edit/',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200 and 'instagram' in response.text.lower():
            # Try to extract username from page
            import re
            match = re.search(r'"username":"([^"]+)"', response.text)
            username = match.group(1) if match else 'instagram_user'
            return True, username, "✅ Valid session"
        
        return False, None, f"❌ Invalid session (HTTP {response.status_code})"
        
    except Exception as e:
        return False, None, f"❌ Error: {str(e)[:50]}"

def get_csrf_token_from_session(session_id):
    """Get CSRF token from Instagram using session"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        response = requests.get(
            'https://www.instagram.com/',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            import re
            # Try multiple patterns to find CSRF token
            patterns = [
                r'"csrf_token":"([^"]+)"',
                r'csrf_token["\']?\s*[:=]\s*["\']([^"\']+)',
                r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']csrf-token["\']',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    csrf_token = match.group(1)
                    if len(csrf_token) > 10:
                        return csrf_token
            
            # Try to get from shared data
            match = re.search(r'window\._sharedData\s*=\s*({.+?});', response.text)
            if match:
                try:
                    data = json.loads(match.group(1))
                    if 'config' in data and 'csrf_token' in data['config']:
                        return data['config']['csrf_token']
                except:
                    pass
        
        return generate_random_string(32)
    except:
        return generate_random_string(32)

def send_instagram_message_2024(session_id, thread_id, message):
    """Updated Instagram message sending method for 2024"""
    try:
        # Get CSRF token
        csrf_token = get_csrf_token_from_session(session_id)
        
        # Generate device ID
        device_id = f"android-{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}"
        
        # Prepare headers
        headers = {
            'authority': 'www.instagram.com',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'cookie': f'sessionid={session_id}; csrftoken={csrf_token}',
            'dpr': '1',
            'origin': 'https://www.instagram.com',
            'referer': f'https://www.instagram.com/direct/t/{thread_id}/',
            'sec-ch-prefers-color-scheme': 'light',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
            'sec-ch-ua-full-version-list': '"Not_A Brand";v="8.0.0.0", "Chromium";v="120.0.6099.130"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-ch-ua-platform-version': '"10.0.0"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'viewport-width': '1920',
            'x-asbd-id': '198387',
            'x-csrftoken': csrf_token,
            'x-ig-app-id': '936619743392459',
            'x-ig-www-claim': '0',
            'x-instagram-ajax': '1008214963',
            'x-requested-with': 'XMLHttpRequest',
        }
        
        # Generate client context
        client_context = hashlib.md5(str(time.time()).encode()).hexdigest()[:32]
        
        # Prepare data - Method 1 (Direct message)
        data = {
            'action': 'send_item',
            'client_context': client_context,
            'device_id': device_id,
            'mutation_token': client_context,
            'nav_chain': f'1q:direct_inbox:1,1q:direct_thread:{thread_id}:2,1q:direct_thread:{thread_id}:3,8Dr:direct_thread:thread_fbid:{thread_id}:4',
            'offline_threading_id': client_context,
            'send_attribution': 'direct_thread',
            'thread_id': thread_id,
            'item_type': 'text',
            'text': message,
        }
        
        # Try Method 1
        response = requests.post(
            'https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/',
            headers=headers,
            data=data,
            timeout=15
        )
        
        if response.status_code == 200:
            return True, "✅ Message sent successfully"
        else:
            # Try Method 2 (Alternative API endpoint)
            return send_instagram_alternative_method(session_id, thread_id, message, csrf_token, device_id)
            
    except Exception as e:
        error_msg = str(e)
        if "HTTPSConnectionPool" in error_msg:
            return False, "❌ Connection error - check internet"
        elif "timed out" in error_msg:
            return False, "❌ Request timed out"
        else:
            return False, f"❌ Error: {error_msg[:50]}"

def send_instagram_alternative_method(session_id, thread_id, message, csrf_token, device_id):
    """Alternative method for sending Instagram messages"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}; csrftoken={csrf_token}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'x-csrftoken': csrf_token,
            'x-ig-app-id': '936619743392459',
            'x-ig-www-claim': '0',
            'x-instagram-ajax': '1008214963',
            'content-type': 'application/x-www-form-urlencoded',
            'x-requested-with': 'XMLHttpRequest',
        }
        
        # Generate unique IDs
        client_context = hashlib.md5(f"{thread_id}{time.time()}".encode()).hexdigest()[:32]
        
        # Alternative data format
        data = {
            'recipient_users': f'[[{thread_id}]]',
            'client_context': client_context,
            'thread_ids': f'[{thread_id}]',
            'action': 'send_item',
            'item_type': 'text',
            'text': message,
            'is_shh_mode': '0',
            'send_attribution': 'direct_thread',
            'entry': 'direct',
        }
        
        response = requests.post(
            'https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/',
            headers=headers,
            data=data,
            timeout=15
        )
        
        if response.status_code == 200:
            return True, "✅ Sent via alternative method"
        elif response.status_code == 400:
            # Try with different endpoint
            return send_instagram_fallback_method(session_id, thread_id, message, csrf_token)
        else:
            return False, f"❌ HTTP {response.status_code}: {response.text[:100]}"
            
    except Exception as e:
        return False, f"❌ Alt error: {str(e)[:30]}"

def send_instagram_fallback_method(session_id, thread_id, message, csrf_token):
    """Fallback method using different endpoint"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}; csrftoken={csrf_token}',
            'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1',
            'x-csrftoken': csrf_token,
            'x-ig-app-id': '124024574287414',
            'content-type': 'application/x-www-form-urlencoded',
        }
        
        # Mobile API format
        data = {
            'recipient_users': f'[["{thread_id}"]]',
            'client_context': f"{int(time.time() * 1000)}",
            'thread_ids': f'["{thread_id}"]',
            'action': 'send_item',
            'item_type': 'text',
            'text': message,
        }
        
        response = requests.post(
            'https://i.instagram.com/api/v1/direct_v2/threads/broadcast/text/',
            headers=headers,
            data=data,
            timeout=15
        )
        
        if response.status_code == 200:
            return True, "✅ Sent via mobile API"
        else:
            return False, f"❌ Fallback HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"❌ Fallback error: {str(e)[:30]}"

def get_thread_id_from_url(url):
    """Extract thread ID from URL"""
    try:
        url = url.strip()
        
        # Remove query parameters
        url = url.split('?')[0]
        
        # Extract from /direct/t/ format
        if '/direct/t/' in url:
            parts = url.split('/direct/t/')
            if len(parts) > 1:
                thread_id = parts[1].strip('/').split('/')[0]
                if thread_id and len(thread_id) > 5:
                    return thread_id
        
        # Try to extract from different URL formats
        import re
        patterns = [
            r'/direct/t/([a-zA-Z0-9_-]+)',
            r'/t/([a-zA-Z0-9_-]+)',
            r'thread/([a-zA-Z0-9_-]+)',
            r'([a-zA-Z0-9_-]{10,})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                thread_id = match.group(1)
                if len(thread_id) >= 10:
                    return thread_id
        
        return None
    except:
        return None

# ========== USER MANAGEMENT WITH 1-HOUR TRIAL ==========
class UserManager:
    def __init__(self):
        self.users_file = Path("users_data.json")
        self.users = self.load_users()
    
    def load_users(self):
        if self.users_file.exists():
            try:
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_users(self):
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(self.users, f, indent=2, ensure_ascii=False)
    
    def add_user(self, user_id: int, username: str = ""):
        user_id_str = str(user_id)
        
        # Always update username if user exists
        if user_id_str in self.users:
            self.users[user_id_str]["username"] = username
            self.save_users()
            return True  # User already exists
        
        # Check if user is admin
        is_admin = (user_id == ADMIN_USER_ID)
        
        # For admin: lifetime access, for others: 1-hour trial
        if is_admin:
            expiry = datetime.now() + timedelta(days=36500)  # 100 years
            plan = "lifetime_admin"
        else:
            expiry = datetime.now() + timedelta(hours=1)  # 1-HOUR TRIAL
            plan = "1_hour_trial"
        
        self.users[user_id_str] = {
            "username": username,
            "plan": plan,
            "expiry": expiry.isoformat(),
            "joined": datetime.now().isoformat(),
            "active": True,
            "is_admin": is_admin,
            "trial_used": True if not is_admin else False
        }
        self.save_users()
        
        # Send trial message to non-admin users
        if not is_admin:
            self.send_trial_message(user_id)
        
        return True
    
    def send_trial_message(self, user_id):
        """Send trial information message"""
        try:
            trial_msg = f"""
⏰ <b>FREE TRIAL ACTIVATED!</b>

You have received <b>1 HOUR FREE TRIAL</b> of {BOT_USERNAME}

After your trial ends, you will need to purchase access.

<b>CONTACT:</b> {CONTACT_USERNAME} for Paid Access of {BOT_USERNAME}

⏳ <b>Trial ends:</b> {(datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')}
"""
            bot.send_message(user_id, trial_msg)
        except:
            pass
    
    def check_access(self, user_id: int):
        """Check if user has access (not expired)"""
        user_id_str = str(user_id)
        
        # Admin always has access
        if user_id == ADMIN_USER_ID:
            return True, "Admin access"
        
        if user_id_str not in self.users:
            return False, "User not found"
        
        user_data = self.users[user_id_str]
        
        # Check if trial expired
        expiry_str = user_data.get("expiry", "")
        if not expiry_str:
            return False, "No expiry date"
        
        try:
            expiry = datetime.fromisoformat(expiry_str)
            if datetime.now() > expiry:
                # Trial expired, deactivate user
                user_data["active"] = False
                self.save_users()
                
                # Send expired message
                self.send_expired_message(user_id)
                return False, "Trial expired"
            
            # Check if still active
            if not user_data.get("active", True):
                return False, "Account deactivated"
            
            return True, "Access granted"
            
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def send_expired_message(self, user_id):
        """Send trial expired message"""
        try:
            expired_msg = f"""
⏰ <b>FREE TRIAL ENDED!</b>

Your 1 hour free trial of {BOT_USERNAME} is now over.

To continue using the bot, you need to purchase access.

<b>CONTACT:</b> {CONTACT_USERNAME} For Paid Access of {BOT_USERNAME}

Thank you for trying our service!
"""
            bot.send_message(user_id, expired_msg)
        except:
            pass
    
    def is_admin(self, user_id: int) -> bool:
        user_id_str = str(user_id)
        
        # Hardcoded admin check
        if user_id == ADMIN_USER_ID:
            return True
        
        user_data = self.users.get(user_id_str)
        if user_data:
            return user_data.get("is_admin", False)
        
        return False
    
    def get_all_users(self):
        return self.users
    
    def get_active_users(self):
        active_users = {}
        for uid, data in self.users.items():
            if data.get("active", True):
                # Check if not expired
                expiry_str = data.get("expiry", "")
                if expiry_str:
                    try:
                        expiry = datetime.fromisoformat(expiry_str)
                        if datetime.now() <= expiry:
                            active_users[uid] = data
                    except:
                        pass
        return active_users
    
    def set_admin(self, user_id: int, is_admin: bool = True):
        user_id_str = str(user_id)
        if user_id_str in self.users:
            self.users[user_id_str]["is_admin"] = is_admin
            self.save_users()
            return True
        return False
    
    def add_user_time(self, user_id: int, hours: int):
        """Add time to user's subscription"""
        user_id_str = str(user_id)
        if user_id_str in self.users:
            expiry = datetime.now() + timedelta(hours=hours)
            self.users[user_id_str]["expiry"] = expiry.isoformat()
            self.users[user_id_str]["active"] = True
            self.save_users()
            return True
        return False
    
    def get_user_time_left(self, user_id: int):
        """Get remaining time for user"""
        user_id_str = str(user_id)
        if user_id_str in self.users:
            expiry_str = self.users[user_id_str].get("expiry", "")
            if expiry_str:
                try:
                    expiry = datetime.fromisoformat(expiry_str)
                    now = datetime.now()
                    if expiry > now:
                        delta = expiry - now
                        hours = delta.total_seconds() / 3600
                        return max(0, hours)
                except:
                    pass
        return 0

# ========== GLOBAL VARIABLES ==========
spam_active = False
success_count = 0
unsuccess_count = 0
counter_lock = threading.Lock()
custom_messages = []
instagram_sessions = []
current_settings = {
    "target": "instagram_user",
    "delay_min": 3,
    "delay_max": 7,
    "message_count": 50,
    "dm_url": "",
    "active_sessions": []
}

# ========== DATA MANAGEMENT ==========
DATA_DIR = Path("instagram_bot_data")
DATA_DIR.mkdir(exist_ok=True)
MESSAGES_FILE = DATA_DIR / "messages.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"

def save_messages():
    try:
        with open(MESSAGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(custom_messages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving messages: {e}")

def load_messages():
    global custom_messages
    try:
        if MESSAGES_FILE.exists():
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                custom_messages = json.load(f)
    except Exception as e:
        print(f"Error loading messages: {e}")
        custom_messages = ["Hello {target}! 👋", "Check this out {target}! 🔥"]

def save_sessions():
    try:
        with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(instagram_sessions, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving sessions: {e}")

def load_sessions():
    global instagram_sessions
    try:
        if SESSIONS_FILE.exists():
            with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                instagram_sessions = json.load(f)
    except Exception as e:
        print(f"Error loading sessions: {e}")
        instagram_sessions = []

# Load data
load_messages()
load_sessions()

# ========== INITIALIZE ==========
user_manager = UserManager()

def initialize_admin():
    """Initialize admin user"""
    admin_id_str = str(ADMIN_USER_ID)
    
    print(f"\n{'='*60}")
    print(f"🤖 BOT INITIALIZATION")
    print(f"Admin User ID: {ADMIN_USER_ID}")
    print(f"Bot Username: {BOT_USERNAME}")
    print(f"Contact: {CONTACT_USERNAME}")
    print(f"{'='*60}\n")
    
    # Ensure admin user exists with lifetime access
    user_manager.add_user(ADMIN_USER_ID, "Admin")
    user_manager.set_admin(ADMIN_USER_ID, True)

initialize_admin()

# ========== HELPER FUNCTIONS ==========
def print_banner():
    return """
╔════════════════════════════════════════════╗
║     INSTAGRAM SPAM BOT v9.0               ║
║     UPDATED 2024 WORKING VERSION          ║
╚════════════════════════════════════════════╝
    """

def check_user_access(chat_id, user_id, command_name=""):
    """Check if user has access to use the bot"""
    user_id_str = str(user_id)
    
    # First, ensure user exists in database
    if user_id_str not in user_manager.users:
        # User doesn't exist - auto-register them
        username = f"User_{user_id}"
        user_manager.add_user(user_id, username)
        print(f"✅ Auto-registered new user: {user_id}")
    
    # Now check access
    has_access, message = user_manager.check_access(user_id)
    
    if not has_access:
        if "expired" in message.lower():
            # Trial expired message
            expired_msg = f"""
⏰ <b>FREE TRIAL ENDED!</b>

Your 1 hour free trial of {BOT_USERNAME} is now over.

To continue using the bot, you need to purchase access.

<b>CONTACT:</b> {CONTACT_USERNAME} For Paid Access of {BOT_USERNAME}

Thank you for trying our service!
"""
            bot.send_message(chat_id, expired_msg)
        else:
            bot.send_message(chat_id, f"❌ <b>Access Denied:</b> {message}")
        return False
    
    return True

def send_start_message(chat_id, user_id=None):
    """Send welcome message"""
    if user_id is None:
        user_id = chat_id
    
    # Check access first
    if not check_user_access(chat_id, user_id, "start"):
        return
    
    is_admin = user_manager.is_admin(user_id)
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    # Get time left for non-admin users
    time_left = ""
    if not is_admin:
        hours_left = user_manager.get_user_time_left(user_id)
        if hours_left > 0:
            time_left = f"⏳ <b>Trial Time Left:</b> {hours_left:.1f} hours\n"
    
    welcome_text = f"""
{print_banner()}

👤 <b>User ID:</b> <code>{user_id}</code>
{'🛡️ <b>Status:</b> ✅ ADMIN USER (Lifetime Access)' if is_admin else '👤 <b>Status:</b> FREE TRIAL USER (1 Hour)'}

{time_left}
📋 <b>AVAILABLE COMMANDS:</b>

🔸 <b>Basic Commands:</b>
/start - Main menu
/help - All commands
/addmsg - Add message
/listmsg - List messages
/sessions - View sessions
/addsession - Add session
/setup - Configure
/start_spam - Start spam
/stop_spam - Stop spam
/stats - Statistics
/timeleft - Check trial time

{'🔸 <b>Admin Commands:</b>' if is_admin else ''}
{'• /admin - Admin panel' if is_admin else ''}
{'• /users - View all users' if is_admin else ''}
{'• /broadcast - Send to all users' if is_admin else ''}

📊 <b>Current Status:</b>
• Messages: {len(custom_messages)}
• Sessions: {valid_sessions}
• Target: {current_settings['target']}
• Spam Active: {'🟢 YES' if spam_active else '🔴 NO'}
"""
    
    # Add trial warning for non-admin
    if not is_admin:
        welcome_text += f"\n⚠️ <b>Note:</b> You have 1-hour free trial. Contact {CONTACT_USERNAME} for paid access."
    
    keyboard_buttons = [
        [InlineKeyboardButton(text="➕ Add Message", callback_data="add_msg"),
         InlineKeyboardButton(text="🔑 Add Session", callback_data="add_session")],
        [InlineKeyboardButton(text="📋 Messages", callback_data="list_msg"),
         InlineKeyboardButton(text="👥 Sessions", callback_data="list_sessions")],
        [InlineKeyboardButton(text="⚙️ Setup", callback_data="setup"),
         InlineKeyboardButton(text="▶️ Start Spam", callback_data="start_spam")],
        [InlineKeyboardButton(text="⏹️ Stop Spam", callback_data="stop_spam"),
         InlineKeyboardButton(text="📊 Stats", callback_data="stats")]
    ]
    
    if is_admin:
        keyboard_buttons.append([InlineKeyboardButton(text="🔐 ADMIN PANEL", callback_data="admin_panel")])
    
    keyboard = InlineKeyboardMarkup()
    for row in keyboard_buttons:
        keyboard.add(*row)
    
    bot.send_message(chat_id, welcome_text, reply_markup=keyboard)

# ========== BASIC COMMANDS ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or "User"
    
    print(f"\n/start command: User {user_id} ({username})")
    
    # Add user to database (will give 1-hour trial for new users)
    user_added = user_manager.add_user(user_id, username)
    
    if user_added and user_id != ADMIN_USER_ID:
        print(f"✅ New user registered: {user_id} ({username}) - 1-hour trial started")
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "start"):
        return
    
    send_start_message(message.chat.id, user_id)

@bot.message_handler(commands=['help'])
def help_command(message):
    """Show all commands"""
    user_id = message.from_user.id
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "help"):
        return
    
    is_admin = user_manager.is_admin(user_id)
    
    help_text = f"""
📚 <b>ALL COMMANDS</b>

🔸 <b>Basic Commands:</b>
/start - Main menu
/help - Show all commands
/addmsg - Add spam message
/listmsg - List all messages
/sessions - View Instagram sessions
/addsession - Add Instagram session
/setup - Configure settings
/start_spam - Start sending messages
/stop_spam - Stop sending messages
/stats - View statistics
/timeleft - Check your trial time left

"""
    
    if is_admin:
        help_text += f"""
🔸 <b>Admin Commands:</b>
/admin - Admin control panel
/users - View all users
/broadcast [message] - Send message to all users
/addtime [user_id] [hours] - Add time to user
"""
    
    help_text += f"\n⏰ <b>Free Trial:</b> 1 hour for new users"
    help_text += f"\n💰 <b>Paid Access:</b> Contact {CONTACT_USERNAME}"
    
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['timeleft'])
def timeleft_command(message):
    """Check trial time left"""
    user_id = message.from_user.id
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "timeleft"):
        return
    
    is_admin = user_manager.is_admin(user_id)
    
    if is_admin:
        bot.send_message(message.chat.id, "🛡️ <b>Admin Status:</b> You have lifetime access!")
    else:
        hours_left = user_manager.get_user_time_left(user_id)
        if hours_left > 0:
            bot.send_message(message.chat.id, 
                f"⏳ <b>Trial Time Left:</b> {hours_left:.1f} hours\n\n"
                f"After trial ends, contact {CONTACT_USERNAME} for paid access."
            )
        else:
            bot.send_message(message.chat.id,
                f"⏰ <b>Trial Expired!</b>\n\n"
                f"Your 1-hour free trial has ended.\n\n"
                f"<b>CONTACT:</b> {CONTACT_USERNAME} for Paid Access of {BOT_USERNAME}"
            )

# ========== ADMIN COMMANDS ==========
@bot.message_handler(commands=['admin'])
def admin_command(message):
    """Admin panel"""
    user_id = message.from_user.id
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "admin"):
        return
    
    # Check if admin
    if not user_manager.is_admin(user_id):
        bot.send_message(message.chat.id, 
            f"❌ <b>Admin Access Required!</b>\n\n"
            f"Your User ID: <code>{user_id}</code>\n"
            f"Contact {CONTACT_USERNAME} for admin access."
        )
        return
    
    username = message.from_user.username or message.from_user.first_name or "Admin"
    
    admin_text = f"""
🔐 <b>ADMIN CONTROL PANEL</b>

✅ <b>Welcome, {username}!</b>
🆔 <b>Your ID:</b> <code>{user_id}</code>

📊 <b>Bot Statistics:</b>
• Total Users: {len(user_manager.get_all_users())}
• Active Users: {len(user_manager.get_active_users())}
• Messages: {len(custom_messages)}
• Sessions: {len(instagram_sessions)}
• Spam Status: {'🟢 Active' if spam_active else '🔴 Inactive'}

⚙️ <b>Admin Commands:</b>
• /users - View all users
• /broadcast [message] - Send to all users
• /addtime [user_id] [hours] - Add time to user

<b>Contact for support:</b> {CONTACT_USERNAME}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="👥 View All Users", callback_data="admin_users"),
        InlineKeyboardButton(text="📊 Full Stats", callback_data="admin_stats")
    )
    keyboard.add(
        InlineKeyboardButton(text="📢 Send Broadcast", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="⏰ Add User Time", callback_data="admin_addtime")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, admin_text, reply_markup=keyboard)

# ... [KEEP ALL THE OTHER FUNCTIONS THE SAME AS BEFORE UNTIL THE SPAM WORKER] ...

def spam_worker(chat_id, thread_id, user_id):
    """Main spam worker function"""
    global spam_active, success_count, unsuccess_count
    
    # Check access periodically
    def check_access_periodically():
        has_access, _ = user_manager.check_access(user_id)
        if not has_access:
            bot.send_message(chat_id, "⏰ <b>Trial expired during spam!</b> Stopping...")
            return False
        return True
    
    # Get valid sessions
    valid_sessions = [s for s in instagram_sessions if s.get('status') == 'valid']
    if not valid_sessions:
        bot.send_message(chat_id, "❌ No valid sessions available!")
        spam_active = False
        return
    
    counter = 0
    session_index = 0
    
    # Check access before starting
    if not check_access_periodically():
        spam_active = False
        return
    
    # Send initial test message
    bot.send_message(chat_id, "🧪 Sending test message...")
    
    test_session = valid_sessions[0]
    test_msg = random.choice(custom_messages) if custom_messages else "Test message from bot"
    formatted_msg = test_msg.replace("{target}", current_settings['target'])
    
    # Use the updated function
    success, result = send_instagram_message_2024(
        test_session.get('session_id'), 
        thread_id, 
        formatted_msg
    )
    
    bot.send_message(chat_id, f"🧪 <b>Test Result:</b> {result}")
    
    if not success:
        bot.send_message(chat_id, 
            "⚠️ <b>Test failed!</b>\n\n"
            "Possible issues:\n"
            "1. Session ID expired\n"
            "2. Thread ID incorrect\n"
            "3. Instagram API rate limit\n\n"
            "Check your session ID and try again."
        )
        spam_active = False
        return
    
    # Main sending loop
    while spam_active and counter < current_settings['message_count']:
        try:
            # Check access every 5 messages
            if counter % 5 == 0 and not check_access_periodically():
                spam_active = False
                break
            
            # Get random message
            msg = random.choice(custom_messages)
            formatted_msg = msg.replace("{target}", current_settings['target'])
            
            # Get next session (round-robin)
            session = valid_sessions[session_index % len(valid_sessions)]
            session_id = session.get('session_id')
            username = session.get('username', 'Account')
            
            # Send message using updated function
            success, result = send_instagram_message_2024(session_id, thread_id, formatted_msg)
            
            counter += 1
            
            if success:
                with counter_lock:
                    success_count += 1
                status = f"✅ Message {counter}: Sent via {username}"
            else:
                with counter_lock:
                    unsuccess_count += 1
                status = f"❌ Message {counter}: {result} via {username}"
            
            # Show first 3 results and progress every 10 messages
            if counter <= 3 or counter % 10 == 0:
                total = success_count + unsuccess_count
                rate = (success_count/total*100) if total > 0 else 0
                
                if counter % 10 == 0:
                    bot.send_message(chat_id,
                        f"📊 <b>Progress Report</b>\n\n"
                        f"Messages sent: {counter}/{current_settings['message_count']}\n"
                        f"✅ Success: {success_count}\n"
                        f"❌ Failed: {unsuccess_count}\n"
                        f"📈 Success Rate: {rate:.1f}%",
                        disable_notification=True
                    )
                else:
                    bot.send_message(chat_id, status, disable_notification=True)
            
            # Move to next session
            session_index += 1
            
            # Wait before next message
            delay = random.uniform(current_settings['delay_min'], current_settings['delay_max'])
            time.sleep(delay)
            
        except Exception as e:
            error_msg = f"❌ Error in spam worker: {str(e)[:100]}"
            print(error_msg)
            time.sleep(2)
    
    # Spam finished
    spam_active = False
    
    # Check if stopped due to trial expiry
    has_access, access_msg = user_manager.check_access(user_id)
    if not has_access and "expired" in access_msg.lower():
        expired_msg = f"""
⏰ <b>FREE TRIAL ENDED!</b>

Your spam was stopped because your 1-hour free trial has expired.

To continue using the bot, purchase access.

<b>CONTACT:</b> {CONTACT_USERNAME} For Paid Access of {BOT_USERNAME}
"""
        bot.send_message(chat_id, expired_msg)
        return
    
    # Final report
    total = success_count + unsuccess_count
    rate = (success_count/total*100) if total > 0 else 0
    
    final_report = f"""
✅ <b>SPAM COMPLETED!</b>

📊 <b>Final Statistics:</b>

• Total Attempted: {counter}
• ✅ Successful: {success_count}
• ❌ Failed: {unsuccess_count}
• 📈 Success Rate: {rate:.1f}%

🎯 <b>Target:</b> {current_settings['target']}
🔗 <b>Thread:</b> {thread_id}

{'🎉 <b>SUCCESS:</b> Messages were sent!' if success_count > 0 else '⚠️ <b>NOTE:</b> Check session IDs if no messages sent.'}

<i>Check your Instagram DM to confirm messages arrived.</i>
"""
    
    bot.send_message(chat_id, final_report)

# ... [KEEP ALL THE REST OF THE CODE THE SAME AS BEFORE] ...

# ========== CALLBACK HANDLERS ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    """Handle all callback queries"""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    username = call.from_user.username or call.from_user.first_name or "User"
    
    print(f"\nCallback received: User {user_id} clicked {call.data}")
    
    # FIRST: Always ensure user exists in database
    user_manager.add_user(user_id, username)
    
    # THEN check access
    has_access, message = user_manager.check_access(user_id)
    if not has_access:
        if "expired" in message.lower():
            expired_msg = f"""
⏰ <b>FREE TRIAL ENDED!</b>

Your 1 hour free trial of {BOT_USERNAME} is now over.

To continue using the bot, you need to purchase access.

<b>CONTACT:</b> {CONTACT_USERNAME} For Paid Access of {BOT_USERNAME}
"""
            bot.send_message(chat_id, expired_msg)
        else:
            bot.send_message(chat_id, f"❌ <b>Access Denied:</b> {message}")
        bot.answer_callback_query(call.id)
        return
    
    bot.answer_callback_query(call.id)  # Acknowledge the click
    
    # Handle different callbacks
    if call.data == "main_menu":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        send_start_message(chat_id, user_id)
    
    elif call.data == "admin_panel":
        admin_command(call.message)
    
    elif call.data == "admin_users":
        users_command(call.message)
    
    elif call.data == "admin_stats":
        stats_command(call.message)
    
    elif call.data == "admin_broadcast":
        msg = bot.send_message(chat_id, "📢 Enter broadcast message:")
        bot.register_next_step_handler(msg, lambda m: broadcast_command_wrapper(m, user_id))
    
    elif call.data == "admin_addtime":
        msg = bot.send_message(chat_id, "⏰ Enter user ID and hours (format: user_id hours):")
        bot.register_next_step_handler(msg, lambda m: addtime_command_wrapper(m, user_id))
    
    elif call.data == "add_msg":
        msg = bot.send_message(chat_id, "✍️ Send message:")
        bot.register_next_step_handler(msg, process_new_message)
    
    elif call.data == "list_msg":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        listmsg_command(call.message)
    
    elif call.data == "add_session":
        msg = bot.send_message(chat_id, "🔑 Send session ID:")
        bot.register_next_step_handler(msg, process_new_session)
    
    elif call.data == "list_sessions":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        sessions_command(call.message)
    
    elif call.data == "setup":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        setup_command(call.message)
    
    elif call.data == "start_spam":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        start_spam_command(call.message)
    
    elif call.data == "stop_spam":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        stop_spam_command(call.message)
    
    elif call.data == "stats":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        stats_command(call.message)
    
    elif call.data == "set_target":
        msg = bot.send_message(chat_id, "🎯 Send target username:")
        bot.register_next_step_handler(msg, process_target)
    
    elif call.data == "set_url":
        msg = bot.send_message(chat_id, "🔗 Send Instagram DM URL:")
        bot.register_next_step_handler(msg, process_url)
    
    elif call.data == "set_count":
        msg = bot.send_message(chat_id, "📊 Send message count (1-1000):")
        bot.register_next_step_handler(msg, process_count)
    
    elif call.data == "set_delay":
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(text="⚡ 0.5-1s (ULTRA FAST)", callback_data="delay_0.5_1"),
            InlineKeyboardButton(text="🚀 1-2s (VERY FAST)", callback_data="delay_1_2")
        )
        keyboard.add(
            InlineKeyboardButton(text="💨 2-3s (FAST)", callback_data="delay_2_3"),
            InlineKeyboardButton(text="🐢 3-5s (NORMAL)", callback_data="delay_3_5")
        )
        bot.send_message(chat_id, "⏱️ Select delay between messages:", reply_markup=keyboard)
    
    elif call.data.startswith("delay_"):
        delays = call.data.split("_")[1:]
        current_settings['delay_min'] = float(delays[0])
        current_settings['delay_max'] = float(delays[1])
        bot.send_message(chat_id, f"✅ Delay: {delays[0]}-{delays[1]} seconds")
    
    elif call.data == "delete_msg_menu":
        if not custom_messages:
            bot.send_message(chat_id, "📭 No messages!")
            return
        
        keyboard = InlineKeyboardMarkup()
        for i in range(min(5, len(custom_messages))):
            preview = custom_messages[i][:30] + "..." if len(custom_messages[i]) > 30 else custom_messages[i]
            keyboard.add(InlineKeyboardButton(text=f"❌ Delete: {preview}", callback_data=f"del_msg_{i}"))
        keyboard.add(InlineKeyboardButton(text="◀️ Back", callback_data="list_msg"))
        
        bot.edit_message_text("🗑️ Select message to delete:", chat_id, call.message.message_id, reply_markup=keyboard)
    
    elif call.data.startswith("del_msg_"):
        try:
            index = int(call.data.split("_")[2])
            custom_messages.pop(index)
            save_messages()
            bot.send_message(chat_id, "✅ Message deleted!")
            listmsg_command(call.message)
        except:
            bot.send_message(chat_id, "❌ Error deleting message!")
    
    elif call.data == "delete_session_menu":
        if not instagram_sessions:
            bot.send_message(chat_id, "🔐 No sessions!")
            return
        
        keyboard = InlineKeyboardMarkup()
        for i in range(len(instagram_sessions)):
            username = instagram_sessions[i].get('username', 'session')
            status = "✅" if instagram_sessions[i].get('status') == 'valid' else "❌"
            keyboard.add(InlineKeyboardButton(text=f"{status} Delete: {username}", callback_data=f"del_sess_{i}"))
        keyboard.add(InlineKeyboardButton(text="◀️ Back", callback_data="sessions"))
        
        bot.edit_message_text("🗑️ Select session to delete:", chat_id, call.message.message_id, reply_markup=keyboard)
    
    elif call.data.startswith("del_sess_"):
        try:
            index = int(call.data.split("_")[2])
            instagram_sessions.pop(index)
            save_sessions()
            bot.send_message(chat_id, "✅ Session deleted!")
            sessions_command(call.message)
        except:
            bot.send_message(chat_id, "❌ Error deleting session!")

# ... [KEEP THE REST OF THE CODE THE SAME] ...

if __name__ == "__main__":
    print(print_banner())
    print(f"🤖 Instagram Spam Bot v9.0 (2024 Working Version)")
    print(f"👑 Admin User ID: {ADMIN_USER_ID}")
    print(f"🤖 Bot Username: {BOT_USERNAME}")
    print(f"📞 Contact: {CONTACT_USERNAME}")
    print(f"⏰ Free Trial: 1 hour for new users")
    print(f"💬 Messages: {len(custom_messages)}")
    print(f"🔑 Sessions: {len(instagram_sessions)}")
    
    try:
        bot_info = bot.get_me()
        print(f"\n✅ Bot Username: @{bot_info.username}")
        print(f"✅ Bot ID: {bot_info.id}")
        print("✅ Bot is ready! Send /start in Telegram")
    except Exception as e:
        print(f"❌ Error connecting to Telegram: {e}")
        print("Please check your bot token and internet connection")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("⚠️ IMPORTANT:")
    print(f"• Admin: {ADMIN_USER_ID} has lifetime access")
    print(f"• New users get 1-hour free trial")
    print(f"• After trial: Contact {CONTACT_USERNAME} for paid access")
    print("="*60 + "\n")
    
    print("🚀 Starting bot polling...")
    bot.infinity_polling()
