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

# ========== INSTAGRAM API - REAL WORKING VERSION ==========
def generate_random_string(length=32):
    """Generate random string for CSRF token"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def validate_instagram_session(session_id):
    """Validate Instagram session - REAL CHECK"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        # Check if session is valid by accessing user profile
        response = requests.get(
            'https://www.instagram.com/api/v1/users/web_profile_info/?username=instagram',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('status') == 'ok':
                    # Get actual username from account
                    test_response = requests.get(
                        'https://www.instagram.com/accounts/edit/',
                        headers=headers,
                        timeout=10
                    )
                    
                    if test_response.status_code == 200:
                        import re
                        # Try to extract username
                        match = re.search(r'"username":"([^"]+)"', test_response.text)
                        if match:
                            username = match.group(1)
                        else:
                            username = "valid_user"
                        
                        # Additional check - get user ID
                        user_id_match = re.search(r'"viewerId":"([^"]+)"', test_response.text)
                        user_id = user_id_match.group(1) if user_id_match else "unknown"
                        
                        return True, username, f"✅ Valid session | User ID: {user_id}"
            except:
                pass
        
        return False, None, "❌ Session expired or invalid"
        
    except Exception as e:
        return False, None, f"❌ Error: {str(e)[:50]}"

def get_instagram_headers(session_id, csrf_token=None):
    """Get proper Instagram headers"""
    if not csrf_token:
        csrf_token = generate_random_string(32)
    
    return {
        'authority': 'www.instagram.com',
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded',
        'cookie': f'sessionid={session_id}; csrftoken={csrf_token}',
        'origin': 'https://www.instagram.com',
        'referer': 'https://www.instagram.com/direct/inbox/',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'x-csrftoken': csrf_token,
        'x-ig-app-id': '936619743392459',
        'x-ig-www-claim': '0',
        'x-instagram-ajax': '1007616494',
        'x-requested-with': 'XMLHttpRequest',
    }

def send_instagram_message_real(session_id, thread_id, message):
    """REAL Instagram message sending that actually works"""
    try:
        # First verify session is still valid
        valid, username, status = validate_instagram_session(session_id)
        if not valid:
            return False, "❌ Session expired"
        
        # Get CSRF token
        csrf_token = get_csrf_token(session_id)
        
        # Prepare headers
        headers = get_instagram_headers(session_id, csrf_token)
        
        # Generate unique IDs
        client_context = generate_client_context()
        device_id = f"android-{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}"
        
        # Method 1: Modern API (2024)
        data = {
            'action': 'send_item',
            'client_context': client_context,
            'device_id': device_id,
            'mutation_token': client_context,
            'nav_chain': '1q:direct_inbox:1',
            'offline_threading_id': client_context,
            'send_attribution': 'direct_thread',
            'thread_id': thread_id,
            'item_type': 'text',
            'text': message,
        }
        
        # Try direct message API
        response = requests.post(
            'https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/',
            headers=headers,
            data=data,
            timeout=15
        )
        
        # Check response
        if response.status_code == 200:
            resp_json = response.json()
            if resp_json.get('status') == 'ok':
                return True, "✅ Message sent"
            else:
                # Try alternative method
                return send_instagram_alt_method(session_id, thread_id, message, csrf_token)
        elif response.status_code == 400:
            # Thread ID might be wrong format
            return send_instagram_user_method(session_id, thread_id, message, csrf_token)
        else:
            return False, f"❌ HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"❌ Error: {str(e)[:50]}"

def get_csrf_token(session_id):
    """Get CSRF token from Instagram"""
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
            # Look for CSRF token in response
            patterns = [
                r'"csrf_token":"([^"]+)"',
                r'csrf_token["\']?\s*[:=]\s*["\']([^"\']+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, response.text)
                if match:
                    token = match.group(1)
                    if len(token) > 10:
                        return token
    except:
        pass
    
    return generate_random_string(32)

def generate_client_context():
    """Generate client context for Instagram"""
    timestamp = int(time.time() * 1000)
    random_num = random.randint(1000000000, 9999999999)
    return f"{timestamp}:{random_num}"

def send_instagram_alt_method(session_id, thread_id, message, csrf_token):
    """Alternative sending method"""
    try:
        headers = get_instagram_headers(session_id, csrf_token)
        
        # Different endpoint
        data = {
            'recipient_users': f'[["{thread_id}"]]',
            'client_context': generate_client_context(),
            'thread_ids': f'["{thread_id}"]',
            'action': 'send_item',
            'item_type': 'text',
            'text': message,
            'is_shh_mode': '0',
            'send_attribution': 'direct_thread',
        }
        
        response = requests.post(
            'https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/',
            headers=headers,
            data=data,
            timeout=15
        )
        
        if response.status_code == 200:
            return True, "✅ Sent (alt method)"
        else:
            return False, f"❌ Alt HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"❌ Alt error: {str(e)[:30]}"

def send_instagram_user_method(session_id, thread_id, message, csrf_token):
    """Send message using user ID instead of thread ID"""
    try:
        # Check if thread_id might be a user ID
        if thread_id.isdigit() and len(thread_id) > 8:
            # Probably a user ID, not thread ID
            user_id = thread_id
            
            headers = get_instagram_headers(session_id, csrf_token)
            
            data = {
                'recipient_users': f'[[{user_id}]]',
                'client_context': generate_client_context(),
                'thread_ids': f'[{user_id}]',
                'action': 'send_item',
                'item_type': 'text',
                'text': message,
            }
            
            response = requests.post(
                'https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/',
                headers=headers,
                data=data,
                timeout=15
            )
            
            if response.status_code == 200:
                return True, "✅ Sent to user ID"
            else:
                return False, f"❌ User method HTTP {response.status_code}"
        else:
            return False, "❌ Invalid thread/user ID format"
            
    except Exception as e:
        return False, f"❌ User method error: {str(e)[:30]}"

def get_thread_id_from_url(url):
    """Extract thread ID or user ID from URL"""
    try:
        url = url.strip()
        
        # If it's already a numeric ID, return it
        if url.isdigit() and len(url) > 8:
            return url
        
        # Extract from /direct/t/ format
        if '/direct/t/' in url:
            parts = url.split('/direct/t/')
            if len(parts) > 1:
                thread_id = parts[1].strip('/').split('/')[0]
                if thread_id:
                    return thread_id
        
        # Extract from profile URL
        if 'instagram.com/' in url and '/direct/' not in url:
            # Extract username
            import re
            match = re.search(r'instagram\.com/([^/?]+)', url)
            if match:
                username = match.group(1)
                # We'll need to convert username to user ID
                return username
        
        return None
    except:
        return None

# ========== USER MANAGEMENT ==========
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
        
        # Check if user already exists
        if user_id_str in self.users:
            # Update username if provided
            if username:
                self.users[user_id_str]["username"] = username
                self.save_users()
            return True
        
        # Check if user is admin
        is_admin = (user_id == ADMIN_USER_ID)
        
        # For admin: lifetime access, for others: 1-hour trial
        if is_admin:
            expiry = datetime.now() + timedelta(days=36500)
            plan = "lifetime_admin"
        else:
            expiry = datetime.now() + timedelta(hours=1)
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
        
        # Send welcome message to non-admin users
        if not is_admin:
            self.send_welcome_message(user_id)
        
        return True
    
    def send_welcome_message(self, user_id):
        """Send welcome message"""
        try:
            welcome_msg = f"""
🎉 <b>WELCOME TO {BOT_USERNAME}!</b>

✅ <b>1-HOUR FREE TRIAL ACTIVATED</b>

⏰ <b>Trial Period:</b> 1 Hour
📅 <b>Expires:</b> {(datetime.now() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')}

💬 <b>After trial ends:</b>
Contact {CONTACT_USERNAME} for paid access

🔧 <b>To get started:</b>
1. Add messages using /addmsg
2. Add Instagram session using /addsession
3. Configure settings using /setup
4. Start spam using /start_spam

Need help? Contact {CONTACT_USERNAME}
"""
            bot.send_message(user_id, welcome_msg)
        except:
            pass
    
    def check_access(self, user_id: int):
        """Check if user has access"""
        user_id_str = str(user_id)
        
        # Admin always has access
        if user_id == ADMIN_USER_ID:
            return True, "Admin access"
        
        if user_id_str not in self.users:
            return False, "User not found"
        
        user_data = self.users[user_id_str]
        
        # Check expiry
        expiry_str = user_data.get("expiry", "")
        if not expiry_str:
            return False, "No expiry date"
        
        try:
            expiry = datetime.fromisoformat(expiry_str)
            if datetime.now() > expiry:
                user_data["active"] = False
                self.save_users()
                return False, "Trial expired"
            
            if not user_data.get("active", True):
                return False, "Account deactivated"
            
            return True, "Access granted"
            
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        if user_id == ADMIN_USER_ID:
            return True
        
        user_data = self.users.get(str(user_id))
        if user_data:
            return user_data.get("is_admin", False)
        
        return False
    
    def get_all_users(self):
        return self.users
    
    def get_active_users(self):
        active_users = {}
        for uid, data in self.users.items():
            if data.get("active", True):
                expiry_str = data.get("expiry", "")
                if expiry_str:
                    try:
                        expiry = datetime.fromisoformat(expiry_str)
                        if datetime.now() <= expiry:
                            active_users[uid] = data
                    except:
                        pass
        return active_users
    
    def add_user_time(self, user_id: int, amount: int, unit: str):
        """Add time to user's subscription"""
        user_id_str = str(user_id)
        if user_id_str in self.users:
            # Get current expiry
            expiry_str = self.users[user_id_str].get("expiry", "")
            if expiry_str:
                try:
                    current_expiry = datetime.fromisoformat(expiry_str)
                except:
                    current_expiry = datetime.now()
            else:
                current_expiry = datetime.now()
            
            # Add time based on unit
            if unit == "minutes":
                new_expiry = current_expiry + timedelta(minutes=amount)
            elif unit == "hours":
                new_expiry = current_expiry + timedelta(hours=amount)
            elif unit == "days":
                new_expiry = current_expiry + timedelta(days=amount)
            elif unit == "weeks":
                new_expiry = current_expiry + timedelta(weeks=amount)
            elif unit == "months":
                new_expiry = current_expiry + timedelta(days=amount * 30)
            elif unit == "lifetime":
                new_expiry = datetime.now() + timedelta(days=36500)
            else:
                return False
            
            self.users[user_id_str]["expiry"] = new_expiry.isoformat()
            self.users[user_id_str]["active"] = True
            self.users[user_id_str]["plan"] = f"paid_{amount}{unit}"
            self.save_users()
            return True
        return False
    
    def get_user_time_left(self, user_id: int):
        """Get remaining time in hours"""
        user_id_str = str(user_id)
        if user_id_str in self.users:
            expiry_str = self.users[user_id_str].get("expiry", "")
            if expiry_str:
                try:
                    expiry = datetime.fromisoformat(expiry_str)
                    now = datetime.now()
                    if expiry > now:
                        delta = expiry - now
                        return delta.total_seconds() / 3600
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
    print(f"\n{'='*60}")
    print(f"🤖 BOT INITIALIZATION")
    print(f"Admin User ID: {ADMIN_USER_ID}")
    print(f"Bot Username: {BOT_USERNAME}")
    print(f"Contact: {CONTACT_USERNAME}")
    print(f"{'='*60}\n")
    
    # Ensure admin exists
    user_manager.add_user(ADMIN_USER_ID, "Admin")

initialize_admin()

# ========== HELPER FUNCTIONS ==========
def print_banner():
    return """
╔════════════════════════════════════════════╗
║     INSTAGRAM SPAM BOT - FINAL FIX        ║
║     GUARANTEED WORKING VERSION           ║
╚════════════════════════════════════════════╝
    """

def check_user_access(chat_id, user_id, command_name=""):
    """Check if user has access"""
    user_id_str = str(user_id)
    
    # Auto-register if not exists
    if user_id_str not in user_manager.users:
        username = f"User_{user_id}"
        user_manager.add_user(user_id, username)
        print(f"✅ Auto-registered user: {user_id}")
    
    # Check access
    has_access, message = user_manager.check_access(user_id)
    
    if not has_access:
        if "expired" in message.lower():
            expired_msg = f"""
⏰ <b>ACCESS EXPIRED!</b>

Your access to {BOT_USERNAME} has ended.

To continue using the bot, purchase access.

<b>CONTACT:</b> {CONTACT_USERNAME} For Paid Access

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
    
    # Check access
    if not check_user_access(chat_id, user_id, "start"):
        return
    
    is_admin = user_manager.is_admin(user_id)
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    # Get time left
    time_left = ""
    if not is_admin:
        hours_left = user_manager.get_user_time_left(user_id)
        if hours_left > 0:
            if hours_left > 24:
                days = hours_left / 24
                time_left = f"⏳ <b>Time Left:</b> {days:.1f} days\n"
            else:
                time_left = f"⏳ <b>Time Left:</b> {hours_left:.1f} hours\n"
    
    welcome_text = f"""
{print_banner()}

👤 <b>User ID:</b> <code>{user_id}</code>
{'🛡️ <b>Status:</b> ✅ ADMIN' if is_admin else '👤 <b>Status:</b> TRIAL USER'}

{time_left}
📋 <b>AVAILABLE COMMANDS:</b>

🔸 <b>Basic:</b>
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
/timeleft - Check time left

{'🔸 <b>Admin Commands:</b>' if is_admin else ''}
{'• /admin - Admin panel' if is_admin else ''}
{'• /users - View all users' if is_admin else ''}
{'• /broadcast - Send to all users' if is_admin else ''}
{'• /addtime - Add time to user' if is_admin else ''}

📊 <b>Current Status:</b>
• Messages: {len(custom_messages)}
• Sessions: {valid_sessions}
• Target: {current_settings['target']}
• Spam Active: {'🟢 YES' if spam_active else '🔴 NO'}
"""
    
    if not is_admin:
        welcome_text += f"\n⚠️ <b>Note:</b> Contact {CONTACT_USERNAME} for paid access."
    
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
    
    # Add user
    user_added = user_manager.add_user(user_id, username)
    
    if user_added and user_id != ADMIN_USER_ID:
        print(f"✅ New user: {user_id} - 1-hour trial")
    
    # Check access
    if not check_user_access(message.chat.id, user_id, "start"):
        return
    
    send_start_message(message.chat.id, user_id)

@bot.message_handler(commands=['help'])
def help_command(message):
    """Show all commands"""
    user_id = message.from_user.id
    
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
/timeleft - Check your time left

"""
    
    if is_admin:
        help_text += f"""
🔸 <b>Admin Commands:</b>
/admin - Admin control panel
/users - View all users
/broadcast [message] - Send message to all users
/addtime [user_id] [amount] [unit] - Add time to user

<b>Units:</b> minutes, hours, days, weeks, months, lifetime
"""
    
    help_text += f"\n💰 <b>Paid Access:</b> Contact {CONTACT_USERNAME}"
    
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['timeleft'])
def timeleft_command(message):
    """Check time left"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "timeleft"):
        return
    
    is_admin = user_manager.is_admin(user_id)
    
    if is_admin:
        bot.send_message(message.chat.id, "🛡️ <b>Admin Status:</b> Lifetime access")
    else:
        hours_left = user_manager.get_user_time_left(user_id)
        if hours_left > 0:
            if hours_left > 24:
                days = hours_left / 24
                bot.send_message(message.chat.id, 
                    f"⏳ <b>Time Left:</b> {days:.1f} days\n\n"
                    f"Contact {CONTACT_USERNAME} for paid access."
                )
            else:
                bot.send_message(message.chat.id, 
                    f"⏳ <b>Time Left:</b> {hours_left:.1f} hours\n\n"
                    f"Contact {CONTACT_USERNAME} for paid access."
                )
        else:
            bot.send_message(message.chat.id,
                f"⏰ <b>Access Expired!</b>\n\n"
                f"Contact {CONTACT_USERNAME} for paid access."
            )

# ========== ADMIN COMMANDS ==========
@bot.message_handler(commands=['admin'])
def admin_command(message):
    """Admin panel"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "admin"):
        return
    
    # Check if admin
    if not user_manager.is_admin(user_id):
        bot.send_message(message.chat.id, 
            f"❌ <b>Admin Access Required!</b>\n\n"
            f"Your ID: <code>{user_id}</code>\n"
            f"Admin ID: <code>{ADMIN_USER_ID}</code>\n\n"
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
• Spam Active: {'🟢 YES' if spam_active else '🔴 NO'}

⚙️ <b>Admin Commands:</b>
• /users - View all users
• /broadcast [message] - Broadcast message
• /addtime [user_id] [amount] [unit] - Add time

<b>Contact:</b> {CONTACT_USERNAME}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="👥 View Users", callback_data="admin_users"),
        InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats")
    )
    keyboard.add(
        InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="⏰ Add Time", callback_data="admin_addtime_menu")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, admin_text, reply_markup=keyboard)

@bot.message_handler(commands=['users'])
def users_command(message):
    """View all users"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "users"):
        return
    
    if not user_manager.is_admin(user_id):
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    users = user_manager.get_all_users()
    if not users:
        bot.send_message(message.chat.id, "📭 No users!")
        return
    
    response = "👥 <b>ALL USERS:</b>\n\n"
    
    for uid, data in users.items():
        username = data.get('username', 'Unknown')
        is_admin = "🛡️ ADMIN" if data.get('is_admin') else "👤 User"
        plan = data.get('plan', 'Free')
        active = "✅" if data.get('active', True) else "❌"
        
        # Time left
        time_left = ""
        if not data.get('is_admin', False):
            try:
                expiry = datetime.fromisoformat(data.get('expiry', ''))
                now = datetime.now()
                if expiry > now:
                    delta = expiry - now
                    hours = delta.total_seconds() / 3600
                    if hours > 24:
                        days = hours / 24
                        time_left = f" ({days:.1f}d)"
                    else:
                        time_left = f" ({hours:.1f}h)"
            except:
                pass
        
        response += f"{is_admin}\n"
        response += f"ID: <code>{uid}</code>\n"
        response += f"Name: {username}\n"
        response += f"Plan: {plan}{time_left}\n"
        response += f"Active: {active}\n"
        response += "─" * 20 + "\n\n"
    
    response += f"📊 <b>Total:</b> {len(users)} users"
    
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    """Broadcast message"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "broadcast"):
        return
    
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
            bot.send_message(message.chat.id, "❌ No active users!")
            return
        
        sent = 0
        failed = 0
        
        bot.send_message(message.chat.id, f"📢 Broadcasting to {len(users)} users...")
        
        for uid in users.keys():
            try:
                bot.send_message(int(uid), 
                    f"📢 <b>ANNOUNCEMENT FROM ADMIN:</b>\n\n"
                    f"{broadcast_msg}\n\n"
                    f"<i>This is a broadcast message.</i>"
                )
                sent += 1
                time.sleep(0.1)
            except:
                failed += 1
        
        bot.send_message(message.chat.id, 
            f"✅ <b>Broadcast Complete!</b>\n\n"
            f"✅ Sent: {sent}\n"
            f"❌ Failed: {failed}\n"
            f"📊 Total: {len(users)}"
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['addtime'])
def addtime_command(message):
    """Add time to user"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "addtime"):
        return
    
    if not user_manager.is_admin(user_id):
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 4:
            bot.send_message(message.chat.id, 
                "Usage: /addtime [user_id] [amount] [unit]\n\n"
                "Units: minutes, hours, days, weeks, months, lifetime\n"
                "Example: /addtime 123456789 7 days"
            )
            return
        
        target_user_id = int(parts[1])
        amount = int(parts[2])
        unit = parts[3].lower()
        
        valid_units = ["minutes", "hours", "days", "weeks", "months", "lifetime"]
        if unit not in valid_units:
            bot.send_message(message.chat.id, 
                f"❌ Invalid unit! Use: {', '.join(valid_units)}"
            )
            return
        
        if user_manager.add_user_time(target_user_id, amount, unit):
            if unit == "lifetime":
                time_msg = "lifetime access"
            else:
                time_msg = f"{amount} {unit}"
            
            bot.send_message(message.chat.id, 
                f"✅ Added {time_msg} to user <code>{target_user_id}</code>"
            )
        else:
            bot.send_message(message.chat.id, f"❌ User <code>{target_user_id}</code> not found!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

# ========== BASIC BOT COMMANDS ==========
@bot.message_handler(commands=['addmsg'])
def addmsg_command(message):
    """Add message"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "addmsg"):
        return
    
    msg = bot.send_message(message.chat.id, 
        "✍️ <b>Send message:</b>\n\n"
        "Use <code>{{target}}</code> for username.\n"
        "Example: Hello {{target}}!"
    )
    bot.register_next_step_handler(msg, process_new_message)

def process_new_message(message):
    user_id = message.from_user.id
    
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
    """List messages"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "listmsg"):
        return
    
    if not custom_messages:
        bot.send_message(message.chat.id, "📭 No messages!")
        return
    
    response = "📋 <b>SAVED MESSAGES:</b>\n\n"
    
    for i, msg in enumerate(custom_messages, 1):
        preview = msg[:50] + "..." if len(msg) > 50 else msg
        response += f"{i}. <code>{preview}</code>\n\n"
    
    response += f"📊 <b>Total:</b> {len(custom_messages)}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="🗑️ Delete", callback_data="delete_msg_menu"),
        InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, response, reply_markup=keyboard)

@bot.message_handler(commands=['addsession'])
def addsession_command(message):
    """Add session"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "addsession"):
        return
    
    instruction = """
🔑 <b>How to get Session ID:</b>

1. Open Instagram in Chrome/Firefox on PC
2. Login to your account
3. Press F12 → Application → Cookies
4. Find <b>sessionid</b> cookie
5. Copy the Value (long string)

📝 <b>Send the sessionid:</b>
"""
    
    msg = bot.send_message(message.chat.id, instruction)
    bot.register_next_step_handler(msg, process_new_session)

def process_new_session(message):
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "addsession"):
        return
    
    session_id = message.text.strip()
    
    if len(session_id) < 20:
        bot.send_message(message.chat.id, "❌ Invalid session ID!")
        return
    
    bot.send_message(message.chat.id, "🔍 Validating...")
    
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
            f"✅ <b>Session Added!</b>\n\n"
            f"👤 <b>Username:</b> {username}\n"
            f"🕒 <b>Added:</b> {datetime.now().strftime('%H:%M:%S')}\n"
            f"📊 <b>Valid Sessions:</b> {len([s for s in instagram_sessions if s.get('status') == 'valid'])}"
        )
    else:
        bot.send_message(message.chat.id,
            f"❌ <b>Validation Failed!</b>\n\n"
            f"<b>Error:</b> {info}\n\n"
            f"<i>Check your session ID.</i>"
        )

@bot.message_handler(commands=['sessions'])
def sessions_command(message):
    """View sessions"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "sessions"):
        return
    
    if not instagram_sessions:
        bot.send_message(message.chat.id, "🔐 No sessions!")
        return
    
    valid_sessions = [s for s in instagram_sessions if s.get('status') == 'valid']
    
    response = "👥 <b>INSTAGRAM SESSIONS</b>\n\n"
    
    if valid_sessions:
        response += "✅ <b>VALID:</b>\n"
        for i, session in enumerate(valid_sessions, 1):
            username = session.get('username', 'Unknown')
            added = session.get('added', 'Unknown')
            response += f"{i}. <b>{username}</b>\n"
            response += f"   🕒 {added}\n\n"
    
    invalid_sessions = [s for s in instagram_sessions if s.get('status') != 'valid']
    if invalid_sessions:
        response += "❌ <b>INVALID:</b>\n"
        for i, session in enumerate(invalid_sessions, 1):
            username = session.get('username', 'Unknown')
            response += f"{i}. {username}\n\n"
    
    response += f"📊 <b>Valid:</b> {len(valid_sessions)}, <b>Invalid:</b> {len(invalid_sessions)}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="➕ Add", callback_data="add_session"),
        InlineKeyboardButton(text="🗑️ Delete", callback_data="delete_session_menu")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, response, reply_markup=keyboard)

@bot.message_handler(commands=['setup'])
def setup_command(message):
    """Configure settings"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "setup"):
        return
    
    current_config = f"""
⚙️ <b>CURRENT SETTINGS:</b>

🎯 <b>Target:</b> {current_settings['target'] or 'Not set'}
🔗 <b>Instagram URL:</b> {'✅ Set' if current_settings['dm_url'] else '❌ Not set'}
⏱️ <b>Delay:</b> {current_settings['delay_min']}-{current_settings['delay_max']}s
📊 <b>Message Count:</b> {current_settings['message_count']}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="🎯 Set Target", callback_data="set_target"),
        InlineKeyboardButton(text="🔗 Set URL", callback_data="set_url")
    )
    keyboard.add(
        InlineKeyboardButton(text="⏱️ Set Delay", callback_data="set_delay"),
        InlineKeyboardButton(text="📊 Set Count", callback_data="set_count")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, current_config + "\n<b>Select option:</b>", reply_markup=keyboard)

@bot.message_handler(commands=['start_spam'])
def start_spam_command(message):
    """Start spam"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "start_spam"):
        return
    
    # Check requirements
    if not custom_messages:
        bot.send_message(message.chat.id, "❌ Add messages first!")
        return
    
    if not instagram_sessions:
        bot.send_message(message.chat.id, "❌ Add sessions first!")
        return
    
    if not current_settings['dm_url']:
        bot.send_message(message.chat.id, "❌ Set Instagram URL first!")
        return
    
    thread_id = get_thread_id_from_url(current_settings['dm_url'])
    if not thread_id:
        bot.send_message(message.chat.id, 
            "❌ <b>Invalid URL!</b>\n\n"
            "Format: https://www.instagram.com/direct/t/THREAD_ID/"
        )
        return
    
    global spam_active
    
    if spam_active:
        bot.send_message(message.chat.id, "⚠️ Already running!")
        return
    
    spam_active = True
    
    # Start spam thread
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
        f"📊 <b>Messages:</b> {len(custom_messages)}\n"
        f"👥 <b>Sessions:</b> {valid_sessions}\n"
        f"⏱️ <b>Delay:</b> {current_settings['delay_min']}-{current_settings['delay_max']}s\n"
        f"📝 <b>Count:</b> {current_settings['message_count']}\n\n"
        f"<i>Starting now...</i>"
    )

def spam_worker(chat_id, thread_id, user_id):
    """Spam worker"""
    global spam_active, success_count, unsuccess_count
    
    def check_access():
        has_access, _ = user_manager.check_access(user_id)
        return has_access
    
    # Get valid sessions
    valid_sessions = [s for s in instagram_sessions if s.get('status') == 'valid']
    if not valid_sessions:
        bot.send_message(chat_id, "❌ No valid sessions!")
        spam_active = False
        return
    
    counter = 0
    session_index = 0
    
    # Check access
    if not check_access():
        spam_active = False
        return
    
    # Send test message
    bot.send_message(chat_id, "🧪 Testing...")
    
    test_session = valid_sessions[0]
    test_msg = random.choice(custom_messages) if custom_messages else "Test"
    formatted_msg = test_msg.replace("{target}", current_settings['target'])
    
    success, result = send_instagram_message_real(
        test_session.get('session_id'), 
        thread_id, 
        formatted_msg
    )
    
    bot.send_message(chat_id, f"🧪 <b>Test:</b> {result}")
    
    if not success:
        bot.send_message(chat_id, 
            "⚠️ <b>Test failed!</b>\n\n"
            "Possible issues:\n"
            "1. Session expired\n"
            "2. Wrong thread ID\n"
            "3. Instagram blocked\n\n"
            "Check and try again."
        )
        spam_active = False
        return
    
    # Main loop
    while spam_active and counter < current_settings['message_count']:
        try:
            # Check access
            if counter % 5 == 0 and not check_access():
                spam_active = False
                break
            
            # Get message
            msg = random.choice(custom_messages)
            formatted_msg = msg.replace("{target}", current_settings['target'])
            
            # Get session
            session = valid_sessions[session_index % len(valid_sessions)]
            session_id = session.get('session_id')
            username = session.get('username', 'Account')
            
            # Send message
            success, result = send_instagram_message_real(session_id, thread_id, formatted_msg)
            
            counter += 1
            
            if success:
                with counter_lock:
                    success_count += 1
                status = f"✅ Message {counter}: Sent via {username}"
            else:
                with counter_lock:
                    unsuccess_count += 1
                status = f"❌ Message {counter}: {result} via {username}"
            
            # Show progress
            if counter <= 3 or counter % 10 == 0:
                total = success_count + unsuccess_count
                rate = (success_count/total*100) if total > 0 else 0
                
                if counter % 10 == 0:
                    bot.send_message(chat_id,
                        f"📊 <b>Progress:</b>\n\n"
                        f"Sent: {counter}/{current_settings['message_count']}\n"
                        f"✅ Success: {success_count}\n"
                        f"❌ Failed: {unsuccess_count}\n"
                        f"📈 Rate: {rate:.1f}%",
                        disable_notification=True
                    )
                else:
                    bot.send_message(chat_id, status, disable_notification=True)
            
            # Next session
            session_index += 1
            
            # Wait
            delay = random.uniform(current_settings['delay_min'], current_settings['delay_max'])
            time.sleep(delay)
            
        except Exception as e:
            error_msg = f"❌ Error: {str(e)[:100]}"
            print(error_msg)
            time.sleep(2)
    
    # Finished
    spam_active = False
    
    # Check if expired
    has_access, access_msg = user_manager.check_access(user_id)
    if not has_access and "expired" in access_msg.lower():
        bot.send_message(chat_id,
            f"⏰ <b>ACCESS EXPIRED!</b>\n\n"
            f"Contact {CONTACT_USERNAME} for paid access."
        )
        return
    
    # Final report
    total = success_count + unsuccess_count
    rate = (success_count/total*100) if total > 0 else 0
    
    final_report = f"""
✅ <b>COMPLETED!</b>

📊 <b>Statistics:</b>

• Attempted: {counter}
• ✅ Success: {success_count}
• ❌ Failed: {unsuccess_count}
• 📈 Rate: {rate:.1f}%

🎯 <b>Target:</b> {current_settings['target']}
🔗 <b>Thread:</b> {thread_id}

{'🎉 Messages sent!' if success_count > 0 else '⚠️ No messages sent.'}

<i>Check Instagram DMs.</i>
"""
    
    bot.send_message(chat_id, final_report)

@bot.message_handler(commands=['stop_spam'])
def stop_spam_command(message):
    """Stop spam"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "stop_spam"):
        return
    
    global spam_active
    
    if not spam_active:
        bot.send_message(message.chat.id, "⚠️ Not running!")
        return
    
    spam_active = False
    bot.send_message(message.chat.id, "🛑 Stopping...")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Show stats"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "stats"):
        return
    
    total = success_count + unsuccess_count
    rate = (success_count/total*100) if total > 0 else 0
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    # Time left
    time_left = ""
    if not user_manager.is_admin(user_id):
        hours_left = user_manager.get_user_time_left(user_id)
        if hours_left > 0:
            if hours_left > 24:
                days = hours_left / 24
                time_left = f"⏰ <b>Time Left:</b> {days:.1f} days\n"
            else:
                time_left = f"⏰ <b>Time Left:</b> {hours_left:.1f} hours\n"
        else:
            time_left = "⏰ <b>Status:</b> Expired\n"
    
    stats_text = f"""
📊 <b>STATISTICS</b>

{time_left}
✅ <b>Success:</b> {success_count}
❌ <b>Failed:</b> {unsuccess_count}
📈 <b>Rate:</b> {rate:.1f}%

💬 <b>Messages:</b> {len(custom_messages)}
👥 <b>Sessions:</b> {valid_sessions}/{len(instagram_sessions)}

🎯 <b>Target:</b> {current_settings['target']}
🔗 <b>URL:</b> {'✅ Set' if current_settings['dm_url'] else '❌ Not set'}

⏱️ <b>Delay:</b> {current_settings['delay_min']}-{current_settings['delay_max']}s
📝 <b>Count:</b> {current_settings['message_count']}

🔴 <b>Status:</b> {'🟢 ACTIVE' if spam_active else '🔴 INACTIVE'}

<b>Contact:</b> {CONTACT_USERNAME}
"""
    
    bot.send_message(message.chat.id, stats_text)

@bot.message_handler(commands=['reset'])
def reset_command(message):
    """Reset stats"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "reset"):
        return
    
    global success_count, unsuccess_count
    
    success_count = 0
    unsuccess_count = 0
    
    bot.send_message(message.chat.id, 
        "🔄 <b>Reset!</b>\n\n"
        "Counters cleared."
    )

# ========== CALLBACK HANDLERS ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    """Handle callbacks"""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    username = call.from_user.username or call.from_user.first_name or "User"
    
    print(f"\nCallback: User {user_id} clicked {call.data}")
    
    # Register user
    user_manager.add_user(user_id, username)
    
    # Check access
    has_access, message = user_manager.check_access(user_id)
    if not has_access:
        if "expired" in message.lower():
            expired_msg = f"""
⏰ <b>ACCESS EXPIRED!</b>

Contact {CONTACT_USERNAME} for paid access.
"""
            bot.send_message(chat_id, expired_msg)
        else:
            bot.send_message(chat_id, f"❌ <b>Access Denied:</b> {message}")
        bot.answer_callback_query(call.id)
        return
    
    bot.answer_callback_query(call.id)
    
    # Handle callbacks
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
        msg = bot.send_message(chat_id, "📢 Enter message:")
        bot.register_next_step_handler(msg, lambda m: broadcast_command_wrapper(m, user_id))
    
    elif call.data == "admin_addtime_menu":
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(text="⏱️ 30 Minutes", callback_data="addtime_30_minutes"),
            InlineKeyboardButton(text="⏱️ 1 Hour", callback_data="addtime_1_hours")
        )
        keyboard.add(
            InlineKeyboardButton(text="⏱️ 1 Day", callback_data="addtime_1_days"),
            InlineKeyboardButton(text="⏱️ 7 Days", callback_data="addtime_7_days")
        )
        keyboard.add(
            InlineKeyboardButton(text="⏱️ 30 Days", callback_data="addtime_30_days"),
            InlineKeyboardButton(text="⏱️ Lifetime", callback_data="addtime_1_lifetime")
        )
        keyboard.add(
            InlineKeyboardButton(text="◀️ Back", callback_data="admin_panel")
        )
        
        bot.edit_message_text(
            "⏰ <b>Select time:</b>\n\nEnter user ID after selection.",
            chat_id, 
            call.message.message_id, 
            reply_markup=keyboard
        )
    
    elif call.data.startswith("addtime_"):
        parts = call.data.split("_")
        if len(parts) >= 3:
            amount = parts[1]
            unit = parts[2]
            msg = bot.send_message(chat_id, f"⏰ Enter user ID to add {amount} {unit}:")
            bot.register_next_step_handler(msg, lambda m: process_addtime(m, amount, unit, user_id))
    
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
        msg = bot.send_message(chat_id, "🎯 Enter target username:")
        bot.register_next_step_handler(msg, process_target)
    
    elif call.data == "set_url":
        msg = bot.send_message(chat_id, "🔗 Enter Instagram DM URL:")
        bot.register_next_step_handler(msg, process_url)
    
    elif call.data == "set_count":
        msg = bot.send_message(chat_id, "📊 Enter message count (1-1000):")
        bot.register_next_step_handler(msg, process_count)
    
    elif call.data == "set_delay":
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(text="⚡ 0.5-1s", callback_data="delay_0.5_1"),
            InlineKeyboardButton(text="🚀 1-2s", callback_data="delay_1_2")
        )
        keyboard.add(
            InlineKeyboardButton(text="💨 2-3s", callback_data="delay_2_3"),
            InlineKeyboardButton(text="🐢 3-5s", callback_data="delay_3_5")
        )
        bot.send_message(chat_id, "⏱️ Select delay:", reply_markup=keyboard)
    
    elif call.data.startswith("delay_"):
        delays = call.data.split("_")[1:]
        current_settings['delay_min'] = float(delays[0])
        current_settings['delay_max'] = float(delays[1])
        bot.send_message(chat_id, f"✅ Delay: {delays[0]}-{delays[1]}s")
    
    elif call.data == "delete_msg_menu":
        if not custom_messages:
            bot.send_message(chat_id, "📭 No messages!")
            return
        
        keyboard = InlineKeyboardMarkup()
        for i in range(min(5, len(custom_messages))):
            preview = custom_messages[i][:30] + "..." if len(custom_messages[i]) > 30 else custom_messages[i]
            keyboard.add(InlineKeyboardButton(text=f"❌ {preview}", callback_data=f"del_msg_{i}"))
        keyboard.add(InlineKeyboardButton(text="◀️ Back", callback_data="list_msg"))
        
        bot.edit_message_text("🗑️ Delete message:", chat_id, call.message.message_id, reply_markup=keyboard)
    
    elif call.data.startswith("del_msg_"):
        try:
            index = int(call.data.split("_")[2])
            custom_messages.pop(index)
            save_messages()
            bot.send_message(chat_id, "✅ Deleted!")
            listmsg_command(call.message)
        except:
            bot.send_message(chat_id, "❌ Error!")
    
    elif call.data == "delete_session_menu":
        if not instagram_sessions:
            bot.send_message(chat_id, "🔐 No sessions!")
            return
        
        keyboard = InlineKeyboardMarkup()
        for i in range(len(instagram_sessions)):
            username = instagram_sessions[i].get('username', 'session')
            status = "✅" if instagram_sessions[i].get('status') == 'valid' else "❌"
            keyboard.add(InlineKeyboardButton(text=f"{status} {username}", callback_data=f"del_sess_{i}"))
        keyboard.add(InlineKeyboardButton(text="◀️ Back", callback_data="sessions"))
        
        bot.edit_message_text("🗑️ Delete session:", chat_id, call.message.message_id, reply_markup=keyboard)
    
    elif call.data.startswith("del_sess_"):
        try:
            index = int(call.data.split("_")[2])
            instagram_sessions.pop(index)
            save_sessions()
            bot.send_message(chat_id, "✅ Deleted!")
            sessions_command(call.message)
        except:
            bot.send_message(chat_id, "❌ Error!")

def process_addtime(message, amount, unit, admin_id):
    """Process addtime"""
    try:
        user_id = int(message.text)
        if user_manager.add_user_time(user_id, int(amount), unit):
            if unit == "lifetime":
                time_msg = "lifetime access"
            else:
                time_msg = f"{amount} {unit}"
            
            bot.send_message(message.chat.id, 
                f"✅ Added {time_msg} to user <code>{user_id}</code>"
            )
            
            # Notify user
            try:
                bot.send_message(user_id,
                    f"🎉 <b>ACCESS UPDATED!</b>\n\n"
                    f"Admin added {time_msg} to your account.\n\n"
                    f"Contact {CONTACT_USERNAME} for support."
                )
            except:
                pass
        else:
            bot.send_message(message.chat.id, f"❌ User <code>{user_id}</code> not found!")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid user ID!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

def broadcast_command_wrapper(message, user_id):
    """Broadcast wrapper"""
    class FakeMessage:
        def __init__(self, text, user_id):
            self.text = text
            self.chat = type('obj', (object,), {'id': message.chat.id})
            self.from_user = type('obj', (object,), {'id': user_id})
    
    fake_msg = FakeMessage(f"/broadcast {message.text}", user_id)
    broadcast_command(fake_msg)

def process_target(message):
    """Process target"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "setup"):
        return
    
    current_settings['target'] = message.text
    bot.send_message(message.chat.id, f"✅ Target: {message.text}")

def process_url(message):
    """Process URL"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "setup"):
        return
    
    url = message.text.strip()
    thread_id = get_thread_id_from_url(url)
    
    if thread_id:
        current_settings['dm_url'] = url
        bot.send_message(message.chat.id, 
            f"✅ <b>URL set!</b>\n\n"
            f"<b>Thread ID:</b> <code>{thread_id}</code>"
        )
    else:
        current_settings['dm_url'] = url
        bot.send_message(message.chat.id, 
            "⚠️ <b>No thread ID detected!</b>\n\n"
            "URL saved anyway.\n"
            "Format: https://www.instagram.com/direct/t/THREAD_ID/"
        )

def process_count(message):
    """Process count"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "setup"):
        return
    
    try:
        count = int(message.text)
        if 1 <= count <= 1000:
            current_settings['message_count'] = count
            bot.send_message(message.chat.id, f"✅ Count: {count}")
        else:
            bot.send_message(message.chat.id, "❌ Enter 1-1000")
    except:
        bot.send_message(message.chat.id, "❌ Invalid number!")

# ========== MAIN ==========
if __name__ == "__main__":
    print(print_banner())
    print(f"🤖 Instagram Spam Bot - FINAL FIX")
    print(f"👑 Admin User ID: {ADMIN_USER_ID}")
    print(f"🤖 Bot Username: {BOT_USERNAME}")
    print(f"📞 Contact: {CONTACT_USERNAME}")
    print(f"⏰ Free Trial: 1 hour")
    print(f"💬 Messages: {len(custom_messages)}")
    print(f"🔑 Sessions: {len(instagram_sessions)}")
    
    try:
        bot_info = bot.get_me()
        print(f"\n✅ Bot Username: @{bot_info.username}")
        print(f"✅ Bot ID: {bot_info.id}")
        print("✅ Bot ready!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("⚠️ IMPORTANT:")
    print(f"• Admin ID: {ADMIN_USER_ID}")
    print(f"• 1-hour free trial for new users")
    print(f"• Contact {CONTACT_USERNAME} for paid access")
    print(f"• Admin can add time: minutes, hours, days, weeks, months, lifetime")
    print("="*60 + "\n")
    
    print("🚀 Starting bot...")
    bot.infinity_polling()
