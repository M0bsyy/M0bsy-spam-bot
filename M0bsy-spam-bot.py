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

# ========== INSTAGRAM API - SIMPLIFIED WORKING VERSION ==========
def generate_random_string(length=32):
    """Generate random string for CSRF token"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def validate_instagram_session(session_id):
    """Simple session validation"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36',
        }
        
        response = requests.get(
            'https://www.instagram.com/accounts/edit/',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200 and 'instagram' in response.text.lower():
            return True, "instagram_user", "✅ Valid session"
        
        return False, None, "❌ Invalid session (Not logged in)"
        
    except Exception as e:
        return False, None, f"❌ Error: {str(e)[:50]}"

def send_instagram_message_working(session_id, thread_id, message):
    """Working Instagram message sending with proper CSRF"""
    try:
        # First get actual CSRF token from Instagram
        csrf_token = extract_real_csrf_token(session_id)
        if not csrf_token:
            csrf_token = generate_random_string(32)
        
        headers = {
            'cookie': f'sessionid={session_id}; csrftoken={csrf_token}',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36',
            'x-csrftoken': csrf_token,
            'x-ig-app-id': '936619743392459',
            'x-ig-www-claim': 'hmac.AR0vFJabfqYQm5ljQkK-OOFpdrqJzucwLrwx9y1KQZbHMFqQ',
            'x-instagram-ajax': '1007616494',
            'x-requested-with': 'XMLHttpRequest',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.instagram.com',
            'referer': 'https://www.instagram.com/direct/inbox/',
            'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
        }
        
        # Generate unique client context
        client_context = f"web:{int(time.time() * 1000)}:{random.randint(1000, 9999)}"
        
        # Correct data format for Instagram API 2024
        data = {
            'recipient_users': f'[["{thread_id}"]]',
            'client_context': client_context,
            'thread_ids': f'["{thread_id}"]',
            'action': 'send_item',
            'item_type': 'text',
            'text': message,
            'entry': 'direct'
        }
        
        response = requests.post(
            'https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/',
            headers=headers,
            data=data,
            timeout=15
        )
        
        # Check response
        if response.status_code == 200:
            return True, "✅ Message sent successfully"
        elif response.status_code == 400:
            # Try alternative format
            return send_instagram_alternative(session_id, thread_id, message, csrf_token)
        else:
            return False, f"❌ HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"❌ Error: {str(e)[:50]}"

def extract_real_csrf_token(session_id):
    """Extract actual CSRF token from Instagram page"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36',
        }
        
        response = requests.get(
            'https://www.instagram.com/',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            # Multiple patterns to find CSRF token
            import re
            
            patterns = [
                r'"csrf_token":"([^"]+)"',
                r'csrf_token["\']?\s*[:=]\s*["\']([^"\']+)',
                r'<meta[^>]*content=["\']([^"\']+)["\'][^>]*name=["\']csrf-token["\']',
                r'window\._sharedData\s*=\s*({[^;]+});'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    if pattern == r'window\._sharedData\s*=\s*({[^;]+});':
                        try:
                            data = json.loads(match.group(1))
                            if 'config' in data and 'csrf_token' in data['config']:
                                return data['config']['csrf_token']
                        except:
                            pass
                    else:
                        return match.group(1)
        
        return None
    except:
        return None

def send_instagram_alternative(session_id, thread_id, message, csrf_token):
    """Alternative sending method"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}; csrftoken={csrf_token}',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36',
            'x-csrftoken': csrf_token,
            'x-ig-app-id': '936619743392459',
            'content-type': 'application/x-www-form-urlencoded',
            'x-requested-with': 'XMLHttpRequest',
        }
        
        # Different data format
        data = {
            'recipient_users': f'[["{thread_id}"]]',
            'client_context': str(int(time.time() * 1000)),
            'thread_ids': f'["{thread_id}"]',
            'action': 'send_item',
            'item_type': 'text',
            'text': message,
            'is_shh_mode': '0',
            'send_attribution': 'direct_thread'
        }
        
        response = requests.post(
            'https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/',
            headers=headers,
            data=data,
            timeout=15
        )
        
        if response.status_code == 200:
            return True, "✅ Sent (alternative method)"
        else:
            return False, f"❌ Alt HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"❌ Alt error: {str(e)[:30]}"

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
        
        # Try to extract any alphanumeric ID
        import re
        match = re.search(r'([a-zA-Z0-9_-]{10,})', url)
        if match:
            return match.group(1)
        
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
║     INSTAGRAM SPAM BOT v8.0               ║
║     1-HOUR FREE TRIAL VERSION             ║
╚════════════════════════════════════════════╝
    """

def ensure_user_exists(user_id, username=""):
    """Ensure user exists in database before checking access"""
    user_id_str = str(user_id)
    if user_id_str not in user_manager.users:
        if not username:
            username = f"User_{user_id}"
        user_manager.add_user(user_id, username)
        print(f"✅ Auto-registered user: {user_id} ({username})")
    return True

def check_user_access(chat_id, user_id, command_name=""):
    """Check if user has access to use the bot"""
    # First ensure user exists
    ensure_user_exists(user_id)
    
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
    
    # Ensure user exists
    ensure_user_exists(user_id)
    
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
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
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
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
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
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
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

@bot.message_handler(commands=['users'])
def users_command(message):
    """View all users - Admin only"""
    user_id = message.from_user.id
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "users"):
        return
    
    # Check if admin
    if not user_manager.is_admin(user_id):
        bot.send_message(message.chat.id, "❌ Admin only command!")
        return
    
    users = user_manager.get_all_users()
    if not users:
        bot.send_message(message.chat.id, "📭 No users in database!")
        return
    
    response = "👥 <b>ALL REGISTERED USERS:</b>\n\n"
    
    for uid, data in users.items():
        username = data.get('username', 'Unknown')
        is_admin = "🛡️ ADMIN" if data.get('is_admin') else "👤 User"
        plan = data.get('plan', 'Free')
        active = "✅" if data.get('active', True) else "❌"
        
        # Get time left
        time_left = ""
        if not data.get('is_admin', False):
            try:
                expiry = datetime.fromisoformat(data.get('expiry', ''))
                now = datetime.now()
                if expiry > now:
                    delta = expiry - now
                    hours = delta.total_seconds() / 3600
                    time_left = f" ({hours:.1f}h left)"
            except:
                pass
        
        response += f"<b>{is_admin}</b>\n"
        response += f"ID: <code>{uid}</code>\n"
        response += f"Name: {username}\n"
        response += f"Plan: {plan}{time_left}\n"
        response += f"Active: {active}\n"
        response += "─" * 20 + "\n\n"
    
    response += f"📊 <b>Total:</b> {len(users)} users"
    
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    """Broadcast message to all users"""
    user_id = message.from_user.id
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "broadcast"):
        return
    
    # Check if admin
    if not user_manager.is_admin(user_id):
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    try:
        parts = message.text.split(' ', 1)
        if len(parts) < 2:
            bot.send_message(message.chat.id, "Usage: /broadcast [message]")
            return
        
        broadcast_msg = parts[1]
        users = user_manager.get_active_users()
        
        if not users:
            bot.send_message(message.chat.id, "❌ No active users to broadcast to!")
            return
        
        sent = 0
        failed = 0
        
        bot.send_message(message.chat.id, f"📢 Broadcasting to {len(users)} users...")
        
        for uid in users.keys():
            try:
                bot.send_message(int(uid), 
                    f"📢 <b>ANNOUNCEMENT FROM ADMIN:</b>\n\n"
                    f"{broadcast_msg}\n\n"
                    f"<i>This is a broadcast message to all users.</i>"
                )
                sent += 1
                time.sleep(0.1)  # Avoid rate limits
            except:
                failed += 1
        
        bot.send_message(message.chat.id, 
            f"✅ <b>Broadcast Complete!</b>\n\n"
            f"✅ Sent: {sent} users\n"
            f"❌ Failed: {failed} users\n"
            f"📊 Total: {len(users)} users"
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['addtime'])
def addtime_command(message):
    """Add time to user's subscription - Admin only"""
    user_id = message.from_user.id
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "addtime"):
        return
    
    # Check if admin
    if not user_manager.is_admin(user_id):
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.send_message(message.chat.id, "Usage: /addtime [user_id] [hours]")
            return
        
        target_user_id = int(parts[1])
        hours = int(parts[2])
        
        if user_manager.add_user_time(target_user_id, hours):
            bot.send_message(message.chat.id, 
                f"✅ Added {hours} hours to user <code>{target_user_id}</code>\n\n"
                f"User now has access for {hours} more hours."
            )
        else:
            bot.send_message(message.chat.id, f"❌ User <code>{target_user_id}</code> not found!")
    except:
        bot.send_message(message.chat.id, "❌ Invalid format! Use: /addtime [user_id] [hours]")

# ========== BASIC BOT COMMANDS ==========
@bot.message_handler(commands=['addmsg'])
def addmsg_command(message):
    """Add message for spamming"""
    user_id = message.from_user.id
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "addmsg"):
        return
    
    msg = bot.send_message(message.chat.id, 
        "✍️ <b>Send the message:</b>\n\n"
        "Use <code>{{target}}</code> for target username.\n"
        "Example: <i>Hello {{target}}!</i>"
    )
    bot.register_next_step_handler(msg, process_new_message)

def process_new_message(message):
    user_id = message.from_user.id
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "addmsg"):
        return
    
    new_message = message.text
    custom_messages.append(new_message)
    save_messages()
    
    bot.send_message(message.chat.id, 
        f"✅ <b>Message Added!</b>\n\n"
        f"Total: {len(custom_messages)} messages"
    )

@bot.message_handler(commands=['listmsg'])
def listmsg_command(message):
    """List all saved messages"""
    user_id = message.from_user.id
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "listmsg"):
        return
    
    if not custom_messages:
        bot.send_message(message.chat.id, "📭 No messages!")
        return
    
    response = "📋 <b>SAVED MESSAGES:</b>\n\n"
    
    for i, msg in enumerate(custom_messages, 1):
        preview = msg[:50] + "..." if len(msg) > 50 else msg
        response += f"{i}. <code>{preview}</code>\n\n"
    
    response += f"📊 <b>Total:</b> {len(custom_messages)} messages"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="🗑️ Delete Messages", callback_data="delete_msg_menu"),
        InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, response, reply_markup=keyboard)

@bot.message_handler(commands=['addsession'])
def addsession_command(message):
    """Add Instagram session"""
    user_id = message.from_user.id
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "addsession"):
        return
    
    instruction = """
🔑 <b>How to get Instagram Session ID:</b>

1. Open Instagram in Chrome/Firefox on PC
2. Login to your account
3. Press F12 for Developer Tools
4. Go to <b>Application</b> tab → <b>Cookies</b> → <b>https://www.instagram.com</b>
5. Look for <b>sessionid</b> cookie
6. Copy the <b>Value</b> (long string)

📝 <b>Send the sessionid value:</b>
"""
    
    msg = bot.send_message(message.chat.id, instruction)
    bot.register_next_step_handler(msg, process_new_session)

def process_new_session(message):
    user_id = message.from_user.id
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "addsession"):
        return
    
    session_id = message.text.strip()
    
    if len(session_id) < 20:
        bot.send_message(message.chat.id, "❌ Invalid session ID! Too short.")
        return
    
    bot.send_message(message.chat.id, "🔍 Validating session...")
    
    valid, username, info = validate_instagram_session(session_id)
    
    if valid:
        session_data = {
            "session_id": session_id,
            "username": username,
            "status": "valid",
            "added": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        instagram_sessions.append(session_data)
        save_sessions()
        
        bot.send_message(message.chat.id, 
            f"✅ <b>Session Added Successfully!</b>\n\n"
            f"👤 <b>Username:</b> {username}\n"
            f"🕒 <b>Added:</b> {datetime.now().strftime('%H:%M:%S')}\n"
            f"📊 <b>Valid Sessions:</b> {len([s for s in instagram_sessions if s.get('status') == 'valid'])}"
        )
    else:
        bot.send_message(message.chat.id,
            f"❌ <b>Session Validation Failed!</b>\n\n"
            f"<b>Error:</b> {info}\n\n"
            f"<i>Please check your session ID and try again.</i>"
        )

@bot.message_handler(commands=['sessions'])
def sessions_command(message):
    """View Instagram sessions"""
    user_id = message.from_user.id
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "sessions"):
        return
    
    if not instagram_sessions:
        bot.send_message(message.chat.id, "🔐 No Instagram sessions saved!")
        return
    
    valid_sessions = [s for s in instagram_sessions if s.get('status') == 'valid']
    
    response = "👥 <b>INSTAGRAM SESSIONS</b>\n\n"
    
    if valid_sessions:
        response += "✅ <b>VALID SESSIONS:</b>\n"
        for i, session in enumerate(valid_sessions, 1):
            username = session.get('username', 'Unknown')
            added = session.get('added', 'Unknown time')
            response += f"{i}. <b>{username}</b>\n"
            response += f"   🕒 {added}\n\n"
    
    invalid_sessions = [s for s in instagram_sessions if s.get('status') != 'valid']
    if invalid_sessions:
        response += "❌ <b>INVALID/TESTING SESSIONS:</b>\n"
        for i, session in enumerate(invalid_sessions, 1):
            username = session.get('username', 'Unknown')
            response += f"{i}. {username}\n\n"
    
    response += f"📊 <b>Summary:</b> {len(valid_sessions)} valid, {len(invalid_sessions)} invalid"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="➕ Add Session", callback_data="add_session"),
        InlineKeyboardButton(text="🗑️ Delete Session", callback_data="delete_session_menu")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, response, reply_markup=keyboard)

@bot.message_handler(commands=['setup'])
def setup_command(message):
    """Configure settings"""
    user_id = message.from_user.id
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "setup"):
        return
    
    current_config = f"""
⚙️ <b>CURRENT SETTINGS:</b>

🎯 <b>Target Username:</b> {current_settings['target'] or 'Not set'}
🔗 <b>Instagram DM URL:</b> {'✅ Set' if current_settings['dm_url'] else '❌ Not set'}
⏱️ <b>Delay between messages:</b> {current_settings['delay_min']}-{current_settings['delay_max']} seconds
📊 <b>Message Count:</b> {current_settings['message_count']} messages
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="🎯 Set Target Username", callback_data="set_target"),
        InlineKeyboardButton(text="🔗 Set Instagram URL", callback_data="set_url")
    )
    keyboard.add(
        InlineKeyboardButton(text="⏱️ Set Message Delay", callback_data="set_delay"),
        InlineKeyboardButton(text="📊 Set Message Count", callback_data="set_count")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, current_config + "\n<b>Select an option to configure:</b>", reply_markup=keyboard)

@bot.message_handler(commands=['start_spam'])
def start_spam_command(message):
    """Start sending messages"""
    user_id = message.from_user.id
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "start_spam"):
        return
    
    # Check requirements
    if not custom_messages:
        bot.send_message(message.chat.id, "❌ Add messages first using /addmsg!")
        return
    
    if not instagram_sessions:
        bot.send_message(message.chat.id, "❌ Add Instagram sessions first using /addsession!")
        return
    
    if not current_settings['dm_url']:
        bot.send_message(message.chat.id, "❌ Set Instagram URL first using /setup!")
        return
    
    thread_id = get_thread_id_from_url(current_settings['dm_url'])
    if not thread_id:
        bot.send_message(message.chat.id, 
            "❌ <b>Invalid Instagram URL!</b>\n\n"
            "Please provide a valid Instagram DM URL in this format:\n"
            "<code>https://www.instagram.com/direct/t/THREAD_ID/</code>"
        )
        return
    
    global spam_active
    
    if spam_active:
        bot.send_message(message.chat.id, "⚠️ Spam is already running!")
        return
    
    spam_active = True
    
    # Start spam in new thread
    thread = threading.Thread(
        target=spam_worker,
        args=(message.chat.id, thread_id, user_id),
        daemon=True
    )
    thread.start()
    
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    bot.send_message(message.chat.id,
        f"✅ <b>SPAM STARTED!</b>\n\n"
        f"🎯 <b>Target:</b> {current_settings['target']}\n"
        f"🔗 <b>Thread ID:</b> <code>{thread_id}</code>\n"
        f"📊 <b>Messages:</b> {len(custom_messages)} available\n"
        f"👥 <b>Accounts:</b> {valid_sessions} valid sessions\n"
        f"⏱️ <b>Delay:</b> {current_settings['delay_min']}-{current_settings['delay_max']} seconds\n"
        f"📝 <b>Target Count:</b> {current_settings['message_count']} messages\n\n"
        f"<i>Messages will start sending now...</i>"
    )

def spam_worker(chat_id, thread_id, user_id):
    """Main spam worker function"""
    global spam_active, success_count, unsuccess_count
    
    # Check access periodically
    def check_access_periodically():
        # Ensure user exists first
        ensure_user_exists(user_id)
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
    
    success, result = send_instagram_message_working(
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
            
            # Send message
            success, result = send_instagram_message_working(session_id, thread_id, formatted_msg)
            
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

@bot.message_handler(commands=['stop_spam'])
def stop_spam_command(message):
    """Stop sending messages"""
    user_id = message.from_user.id
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "stop_spam"):
        return
    
    global spam_active
    
    if not spam_active:
        bot.send_message(message.chat.id, "⚠️ No active spam to stop!")
        return
    
    spam_active = False
    bot.send_message(message.chat.id, "🛑 Stopping spam... Current message will finish.")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Show statistics"""
    user_id = message.from_user.id
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "stats"):
        return
    
    total = success_count + unsuccess_count
    rate = (success_count/total*100) if total > 0 else 0
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    # Get user time left if not admin
    time_left_info = ""
    if not user_manager.is_admin(user_id):
        hours_left = user_manager.get_user_time_left(user_id)
        if hours_left > 0:
            time_left_info = f"⏰ <b>Trial Time Left:</b> {hours_left:.1f} hours\n"
        else:
            time_left_info = f"⏰ <b>Trial Status:</b> Expired\n"
    
    stats_text = f"""
📊 <b>BOT STATISTICS</b>

{time_left_info}
✅ <b>Messages Sent Successfully:</b> {success_count}
❌ <b>Messages Failed:</b> {unsuccess_count}
📈 <b>Success Rate:</b> {rate:.1f}%

💬 <b>Saved Messages:</b> {len(custom_messages)}
👥 <b>Instagram Sessions:</b> {valid_sessions} valid / {len(instagram_sessions)} total

🎯 <b>Current Target:</b> {current_settings['target']}
🔗 <b>Instagram URL:</b> {'✅ Set' if current_settings['dm_url'] else '❌ Not set'}

⏱️ <b>Message Delay:</b> {current_settings['delay_min']}-{current_settings['delay_max']} seconds
📝 <b>Target Count:</b> {current_settings['message_count']} messages

🔴 <b>Spam Status:</b> {'🟢 ACTIVE' if spam_active else '🔴 INACTIVE'}

<b>Contact for support:</b> {CONTACT_USERNAME}
"""
    
    bot.send_message(message.chat.id, stats_text)

@bot.message_handler(commands=['reset'])
def reset_command(message):
    """Reset statistics"""
    user_id = message.from_user.id
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "reset"):
        return
    
    global success_count, unsuccess_count
    
    success_count = 0
    unsuccess_count = 0
    
    bot.send_message(message.chat.id, 
        "🔄 <b>Statistics Reset!</b>\n\n"
        "✅ Success count: 0\n"
        "❌ Failure count: 0\n\n"
        "All counters have been reset to zero."
    )

# ========== CALLBACK HANDLERS ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    """Handle all callback queries"""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    username = call.from_user.username or call.from_user.first_name or "User"
    
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
    
    if call.data == "main_menu":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        send_start_message(chat_id, user_id)
    
    elif call.data == "admin_panel":
        # Create fake message for admin command
        class FakeMessage:
            def __init__(self, chat_id, user_id, username):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {
                    'id': user_id,
                    'username': username or 'User',
                    'first_name': username or 'User'
                })
                self.text = "/admin"
        
        fake_msg = FakeMessage(chat_id, user_id, username)
        admin_command(fake_msg)
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_users":
        # Create fake message for users command
        class FakeMessage:
            def __init__(self, chat_id, user_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {'id': user_id})
        
        fake_msg = FakeMessage(chat_id, user_id)
        users_command(fake_msg)
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_stats":
        # Create fake message for stats command
        class FakeMessage:
            def __init__(self, chat_id, user_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {'id': user_id})
                self.text = "/stats"
        
        fake_msg = FakeMessage(chat_id, user_id)
        stats_command(fake_msg)
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_broadcast":
        msg = bot.send_message(chat_id, "📢 Enter broadcast message:")
        bot.register_next_step_handler(msg, lambda m: broadcast_command_wrapper(m, user_id))
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_addtime":
        msg = bot.send_message(chat_id, "⏰ Enter user ID and hours (format: user_id hours):")
        bot.register_next_step_handler(msg, lambda m: addtime_command_wrapper(m, user_id))
        bot.answer_callback_query(call.id)
    
    elif call.data == "add_msg":
        msg = bot.send_message(chat_id, "✍️ Send message:")
        bot.register_next_step_handler(msg, process_new_message)
        bot.answer_callback_query(call.id)
    
    elif call.data == "list_msg":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        # Create fake message
        class FakeMessage:
            def __init__(self, chat_id, user_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {'id': user_id})
                self.text = "/listmsg"
        
        fake_msg = FakeMessage(chat_id, user_id)
        listmsg_command(fake_msg)
    
    elif call.data == "add_session":
        msg = bot.send_message(chat_id, "🔑 Send session ID:")
        bot.register_next_step_handler(msg, process_new_session)
        bot.answer_callback_query(call.id)
    
    elif call.data == "list_sessions":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        # Create fake message
        class FakeMessage:
            def __init__(self, chat_id, user_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {'id': user_id})
                self.text = "/sessions"
        
        fake_msg = FakeMessage(chat_id, user_id)
        sessions_command(fake_msg)
    
    elif call.data == "setup":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        # Create fake message
        class FakeMessage:
            def __init__(self, chat_id, user_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {'id': user_id})
                self.text = "/setup"
        
        fake_msg = FakeMessage(chat_id, user_id)
        setup_command(fake_msg)
    
    elif call.data == "start_spam":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        # Create fake message
        class FakeMessage:
            def __init__(self, chat_id, user_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {'id': user_id})
                self.text = "/start_spam"
        
        fake_msg = FakeMessage(chat_id, user_id)
        start_spam_command(fake_msg)
    
    elif call.data == "stop_spam":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        # Create fake message
        class FakeMessage:
            def __init__(self, chat_id, user_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {'id': user_id})
                self.text = "/stop_spam"
        
        fake_msg = FakeMessage(chat_id, user_id)
        stop_spam_command(fake_msg)
    
    elif call.data == "stats":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        # Create fake message
        class FakeMessage:
            def __init__(self, chat_id, user_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {'id': user_id})
                self.text = "/stats"
        
        fake_msg = FakeMessage(chat_id, user_id)
        stats_command(fake_msg)
    
    elif call.data == "set_target":
        msg = bot.send_message(chat_id, "🎯 Send target username:")
        bot.register_next_step_handler(msg, process_target)
        bot.answer_callback_query(call.id)
    
    elif call.data == "set_url":
        msg = bot.send_message(chat_id, "🔗 Send Instagram DM URL:")
        bot.register_next_step_handler(msg, process_url)
        bot.answer_callback_query(call.id)
    
    elif call.data == "set_count":
        msg = bot.send_message(chat_id, "📊 Send message count (1-1000):")
        bot.register_next_step_handler(msg, process_count)
        bot.answer_callback_query(call.id)
    
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
        bot.answer_callback_query(call.id)
    
    elif call.data.startswith("delay_"):
        delays = call.data.split("_")[1:]
        current_settings['delay_min'] = float(delays[0])
        current_settings['delay_max'] = float(delays[1])
        bot.send_message(chat_id, f"✅ Delay: {delays[0]}-{delays[1]} seconds")
        bot.answer_callback_query(call.id)
    
    elif call.data == "delete_msg_menu":
        if not custom_messages:
            bot.answer_callback_query(call.id, "No messages!")
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
            bot.answer_callback_query(call.id, "✅ Message deleted!")
            # Create fake message for listmsg
            class FakeMessage:
                def __init__(self, chat_id, user_id):
                    self.chat = type('obj', (object,), {'id': chat_id})
                    self.from_user = type('obj', (object,), {'id': user_id})
                    self.text = "/listmsg"
            
            fake_msg = FakeMessage(chat_id, user_id)
            listmsg_command(fake_msg)
        except:
            bot.answer_callback_query(call.id, "❌ Error!")
    
    elif call.data == "delete_session_menu":
        if not instagram_sessions:
            bot.answer_callback_query(call.id, "No sessions!")
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
            bot.answer_callback_query(call.id, "✅ Session deleted!")
            # Create fake message for sessions
            class FakeMessage:
                def __init__(self, chat_id, user_id):
                    self.chat = type('obj', (object,), {'id': chat_id})
                    self.from_user = type('obj', (object,), {'id': user_id})
                    self.text = "/sessions"
            
            fake_msg = FakeMessage(chat_id, user_id)
            sessions_command(fake_msg)
        except:
            bot.answer_callback_query(call.id, "❌ Error!")
    
    else:
        bot.answer_callback_query(call.id)

def broadcast_command_wrapper(message, user_id):
    """Wrapper for broadcast command from callback"""
    class FakeMessage:
        def __init__(self, text, user_id):
            self.text = text
            self.chat = type('obj', (object,), {'id': message.chat.id})
            self.from_user = type('obj', (object,), {'id': user_id})
    
    fake_msg = FakeMessage(f"/broadcast {message.text}", user_id)
    broadcast_command(fake_msg)

def addtime_command_wrapper(message, user_id):
    """Wrapper for addtime command from callback"""
    class FakeMessage:
        def __init__(self, text, user_id):
            self.text = text
            self.chat = type('obj', (object,), {'id': message.chat.id})
            self.from_user = type('obj', (object,), {'id': user_id})
    
    fake_msg = FakeMessage(f"/addtime {message.text}", user_id)
    addtime_command(fake_msg)

# ========== MESSAGE HANDLERS ==========
def process_target(message):
    user_id = message.from_user.id
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "setup"):
        return
    
    current_settings['target'] = message.text
    bot.send_message(message.chat.id, f"✅ Target set to: {message.text}")

def process_url(message):
    user_id = message.from_user.id
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "setup"):
        return
    
    url = message.text.strip()
    thread_id = get_thread_id_from_url(url)
    
    if thread_id:
        current_settings['dm_url'] = url
        bot.send_message(message.chat.id, 
            f"✅ <b>URL set successfully!</b>\n\n"
            f"<b>Thread ID detected:</b> <code>{thread_id}</code>"
        )
    else:
        bot.send_message(message.chat.id, 
            "⚠️ <b>Could not detect Thread ID from URL!</b>\n\n"
            "But the URL has been saved anyway.\n"
            "Make sure the URL is in this format:\n"
            "<code>https://www.instagram.com/direct/t/THREAD_ID/</code>"
        )
        current_settings['dm_url'] = url

def process_count(message):
    user_id = message.from_user.id
    
    # Ensure user exists
    ensure_user_exists(user_id, message.from_user.username or message.from_user.first_name)
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "setup"):
        return
    
    try:
        count = int(message.text)
        if 1 <= count <= 1000:
            current_settings['message_count'] = count
            bot.send_message(message.chat.id, f"✅ Message count set to: {count}")
        else:
            bot.send_message(message.chat.id, "❌ Please enter a number between 1 and 1000")
    except:
        bot.send_message(message.chat.id, "❌ Please enter a valid number!")

# ========== MAIN FUNCTION ==========
if __name__ == "__main__":
    print(print_banner())
    print(f"🤖 Instagram Spam Bot v8.0")
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
