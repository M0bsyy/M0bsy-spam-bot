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
ADMIN_USER_ID = 6107382622  # YOUR TELEGRAM USER ID - MUST WORK
BOT_USERNAME = "@M0bsy_spam_bot"
CONTACT_USERNAME = "@M0bsy_olds"

# Initialize bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# ========== INSTAGRAM API - UPDATED 2024 WORKING VERSION ==========
def validate_instagram_session(session_id):
    """Validate Instagram session"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        response = requests.get(
            'https://www.instagram.com/api/v1/users/web_profile_info/?username=instagram',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('status') == 'ok':
                    return True, "instagram_user", "✅ Valid session"
            except:
                pass
        
        # Alternative check
        response = requests.get(
            'https://www.instagram.com/accounts/edit/',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200 and 'instagram' in response.text.lower():
            return True, "instagram_user", "✅ Valid session"
        
        return False, None, "❌ Invalid session"
        
    except Exception as e:
        return False, None, f"❌ Error: {str(e)[:30]}"

def send_instagram_dm(session_id, thread_id, message):
    """Send Instagram DM - UPDATED 2024 WORKING METHOD"""
    try:
        # Get CSRF token
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        # Get main page to extract CSRF
        response = requests.get(
            'https://www.instagram.com/',
            headers=headers,
            timeout=10
        )
        
        csrf_token = ""
        if response.status_code == 200:
            import re
            match = re.search(r'"csrf_token":"([^"]+)"', response.text)
            if match:
                csrf_token = match.group(1)
        
        if not csrf_token:
            csrf_token = "missing"
        
        # Updated headers for 2024
        headers = {
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
        
        # Generate unique IDs
        client_context = f"{int(time.time() * 1000)}"
        device_id = f"android-{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}"
        
        # Method 1: New API format
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
        
        response = requests.post(
            'https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/',
            headers=headers,
            data=data,
            timeout=15
        )
        
        if response.status_code == 200:
            return True, "✅ Message sent"
        elif response.status_code == 400:
            # Try alternative format
            return send_instagram_alternative(session_id, thread_id, message, csrf_token)
        else:
            return False, f"❌ HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"❌ Error: {str(e)[:30]}"

def send_instagram_alternative(session_id, thread_id, message, csrf_token):
    """Alternative sending method"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}; csrftoken={csrf_token}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'x-csrftoken': csrf_token,
            'x-ig-app-id': '936619743392459',
            'content-type': 'application/x-www-form-urlencoded',
            'x-requested-with': 'XMLHttpRequest',
        }
        
        data = {
            'recipient_users': f'[["{thread_id}"]]',
            'client_context': f"{int(time.time() * 1000)}",
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

def get_thread_id_from_url(url):
    """Extract thread ID from URL"""
    try:
        url = url.strip()
        
        # If numeric, return as is
        if url.isdigit() and len(url) > 8:
            return url
        
        # Extract from /direct/t/ format
        if '/direct/t/' in url:
            parts = url.split('/direct/t/')
            if len(parts) > 1:
                thread_id = parts[1].strip('/').split('/')[0]
                if thread_id:
                    return thread_id
        
        # Try to extract any ID
        import re
        match = re.search(r'([0-9]+)', url)
        if match:
            return match.group(1)
        
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
        
        # Check if admin
        is_admin = (user_id == ADMIN_USER_ID)
        
        # If user exists, update
        if user_id_str in self.users:
            if is_admin:
                self.users[user_id_str]["is_admin"] = True
                self.users[user_id_str]["plan"] = "lifetime_admin"
                self.users[user_id_str]["expiry"] = (datetime.now() + timedelta(days=36500)).isoformat()
                self.users[user_id_str]["active"] = True
            self.users[user_id_str]["username"] = username
            self.save_users()
            return True
        
        # Create new user
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
        
        return True
    
    def check_access(self, user_id: int):
        """Check access - ADMIN ALWAYS HAS ACCESS"""
        if user_id == ADMIN_USER_ID:
            return True, "Admin access"
        
        user_id_str = str(user_id)
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
            
        except:
            return False, "Error"
    
    def is_admin(self, user_id: int) -> bool:
        """Check if admin"""
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
        """Add time to user"""
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
            
            # Add time
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

# ========== GLOBAL VARIABLES ==========
spam_active = False
success_count = 0
unsuccess_count = 0
counter_lock = threading.Lock()
custom_messages = []
instagram_sessions = []
current_settings = {
    "target": "instagram_user",
    "delay_min": 2,
    "delay_max": 5,
    "dm_url": "",
    "continuous_mode": True,  # NEW: Continuous spam mode
    "messages_sent": 0  # Track total messages sent
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
    except:
        pass

def load_messages():
    global custom_messages
    try:
        if MESSAGES_FILE.exists():
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                custom_messages = json.load(f)
    except:
        custom_messages = ["Hello {target}! 👋", "Check this out {target}! 🔥", "Welcome {target}! 🎉"]

def save_sessions():
    try:
        with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(instagram_sessions, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_sessions():
    global instagram_sessions
    try:
        if SESSIONS_FILE.exists():
            with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                instagram_sessions = json.load(f)
    except:
        instagram_sessions = []

# Load data
load_messages()
load_sessions()

# ========== INITIALIZE ==========
user_manager = UserManager()

def initialize_admin():
    """Initialize admin"""
    print(f"\n{'='*60}")
    print(f"🤖 INSTAGRAM SPAM BOT")
    print(f"🔑 ADMIN ID: {ADMIN_USER_ID}")
    print(f"🤖 Bot: {BOT_USERNAME}")
    print(f"{'='*60}\n")
    
    # Force add admin
    user_manager.add_user(ADMIN_USER_ID, "ADMIN")

initialize_admin()

# ========== HELPER FUNCTIONS ==========
def check_user_access(chat_id, user_id, command_name=""):
    """Check access - ADMIN ALWAYS PASSES"""
    user_id_str = str(user_id)
    
    # Auto-register
    if user_id_str not in user_manager.users:
        username = f"User_{user_id}"
        user_manager.add_user(user_id, username)
    
    # Admin always passes
    if user_id == ADMIN_USER_ID:
        return True
    
    # Check regular users
    has_access, message = user_manager.check_access(user_id)
    
    if not has_access:
        if "expired" in message.lower():
            bot.send_message(chat_id,
                f"⏰ <b>ACCESS EXPIRED!</b>\n\n"
                f"Contact {CONTACT_USERNAME} for paid access."
            )
        else:
            bot.send_message(chat_id, f"❌ <b>Access Denied:</b> {message}")
        return False
    
    return True

def send_start_message(chat_id, user_id=None):
    """Send start message"""
    if user_id is None:
        user_id = chat_id
    
    if not check_user_access(chat_id, user_id, "start"):
        return
    
    is_admin = user_manager.is_admin(user_id)
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    welcome_text = f"""
╔════════════════════════════════════════════╗
║     INSTAGRAM SPAM BOT v2.0              ║
║     CONTINUOUS SPAM MODE                 ║
╚════════════════════════════════════════════╝

👤 <b>User ID:</b> <code>{user_id}</code>
{'🛡️ <b>Status:</b> ✅ ADMIN (Lifetime)' if is_admin else '👤 <b>Status:</b> Trial'}

📋 <b>Commands:</b>
/start - Main menu
/addmsg - Add message
/listmsg - List messages
/addsession - Add session
/sessions - View sessions
/setup - Configure
/start_spam - 🚀 START CONTINUOUS SPAM
/stop_spam - 🛑 STOP SPAM
/stats - Statistics

{'🔸 <b>Admin Commands:</b>' if is_admin else ''}
{'• /admin - Admin panel' if is_admin else ''}
{'• /users - View users' if is_admin else ''}
{'• /addtime - Add time to users' if is_admin else ''}

📊 <b>Status:</b>
• Messages: {len(custom_messages)}
• Sessions: {valid_sessions}
• Target: {current_settings['target']}
• Spam: {'🟢 RUNNING' if spam_active else '🔴 STOPPED'}
• Mode: {'♾️ CONTINUOUS' if current_settings['continuous_mode'] else '📊 LIMITED'}
• Sent: {current_settings['messages_sent']} messages
"""
    
    keyboard_buttons = [
        [InlineKeyboardButton(text="➕ Add Message", callback_data="add_msg"),
         InlineKeyboardButton(text="🔑 Add Session", callback_data="add_session")],
        [InlineKeyboardButton(text="📋 Messages", callback_data="list_msg"),
         InlineKeyboardButton(text="👥 Sessions", callback_data="list_sessions")],
        [InlineKeyboardButton(text="⚙️ Setup", callback_data="setup"),
         InlineKeyboardButton(text="🚀 Start Spam", callback_data="start_spam")],
        [InlineKeyboardButton(text="🛑 Stop Spam", callback_data="stop_spam"),
         InlineKeyboardButton(text="📊 Stats", callback_data="stats")]
    ]
    
    if is_admin:
        keyboard_buttons.append([InlineKeyboardButton(text="🔐 ADMIN", callback_data="admin_panel")])
    
    keyboard = InlineKeyboardMarkup()
    for row in keyboard_buttons:
        keyboard.add(*row)
    
    bot.send_message(chat_id, welcome_text, reply_markup=keyboard)

# ========== BASIC COMMANDS ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or "User"
    
    print(f"\n/start: User {user_id}")
    
    user_manager.add_user(user_id, username)
    send_start_message(message.chat.id, user_id)

@bot.message_handler(commands=['addmsg'])
def addmsg_command(message):
    """Add message"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "addmsg"):
        return
    
    msg = bot.send_message(message.chat.id, "✍️ <b>Send message:</b>\nUse {target} for username")
    bot.register_next_step_handler(msg, process_new_message)

def process_new_message(message):
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "addmsg"):
        return
    
    new_message = message.text
    custom_messages.append(new_message)
    save_messages()
    
    bot.send_message(message.chat.id, f"✅ Added! Total: {len(custom_messages)}")

@bot.message_handler(commands=['listmsg'])
def listmsg_command(message):
    """List messages"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "listmsg"):
        return
    
    if not custom_messages:
        bot.send_message(message.chat.id, "📭 No messages!")
        return
    
    response = "📋 <b>MESSAGES:</b>\n\n"
    
    for i, msg in enumerate(custom_messages, 1):
        preview = msg[:50] + "..." if len(msg) > 50 else msg
        response += f"{i}. <code>{preview}</code>\n\n"
    
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['addsession'])
def addsession_command(message):
    """Add session"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "addsession"):
        return
    
    instruction = """
🔑 <b>Get Session ID:</b>

1. Open Instagram in Chrome
2. Login to account
3. Press F12 → Application → Cookies
4. Find <b>sessionid</b>
5. Copy the value

📝 <b>Send sessionid:</b>
"""
    
    msg = bot.send_message(message.chat.id, instruction)
    bot.register_next_step_handler(msg, process_new_session)

def process_new_session(message):
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "addsession"):
        return
    
    session_id = message.text.strip()
    
    if len(session_id) < 20:
        bot.send_message(message.chat.id, "❌ Invalid!")
        return
    
    bot.send_message(message.chat.id, "🔍 Validating...")
    
    valid, username, info = validate_instagram_session(session_id)
    
    if valid:
        session_data = {
            "session_id": session_id,
            "username": username,
            "status": "valid",
            "added": datetime.now().strftime("%H:%M:%S")
        }
        instagram_sessions.append(session_data)
        save_sessions()
        
        bot.send_message(message.chat.id, 
            f"✅ <b>Added!</b>\n"
            f"👤 {username}\n"
            f"🕒 {datetime.now().strftime('%H:%M:%S')}"
        )
    else:
        bot.send_message(message.chat.id, f"❌ Failed: {info}")

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
    
    response = "👥 <b>SESSIONS:</b>\n\n"
    
    if valid_sessions:
        response += "✅ <b>VALID:</b>\n"
        for i, session in enumerate(valid_sessions, 1):
            username = session.get('username', 'Unknown')
            added = session.get('added', 'Unknown')
            response += f"{i}. <b>{username}</b>\n"
            response += f"   🕒 {added}\n\n"
    
    response += f"📊 <b>Valid:</b> {len(valid_sessions)}"
    
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['setup'])
def setup_command(message):
    """Setup"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "setup"):
        return
    
    current_config = f"""
⚙️ <b>SETTINGS:</b>

🎯 <b>Target:</b> {current_settings['target']}
🔗 <b>URL:</b> {'✅ Set' if current_settings['dm_url'] else '❌ Not set'}
⏱️ <b>Delay:</b> {current_settings['delay_min']}-{current_settings['delay_max']}s
♾️ <b>Mode:</b> {'CONTINUOUS' if current_settings['continuous_mode'] else 'LIMITED'}
📊 <b>Sent:</b> {current_settings['messages_sent']} messages
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="🎯 Target", callback_data="set_target"),
        InlineKeyboardButton(text="🔗 URL", callback_data="set_url")
    )
    keyboard.add(
        InlineKeyboardButton(text="⏱️ Delay", callback_data="set_delay"),
        InlineKeyboardButton(text="♾️ Mode", callback_data="toggle_mode")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, current_config + "\n<b>Select:</b>", reply_markup=keyboard)

@bot.message_handler(commands=['start_spam'])
def start_spam_command(message):
    """🚀 START CONTINUOUS SPAM"""
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
            "Format: https://www.instagram.com/direct/t/THREAD_ID/\n"
            "or just the thread ID: 17850716417587515"
        )
        return
    
    global spam_active
    
    if spam_active:
        bot.send_message(message.chat.id, "⚠️ Already running!")
        return
    
    spam_active = True
    
    # Start spam thread
    thread = threading.Thread(
        target=continuous_spam_worker,
        args=(message.chat.id, thread_id, user_id),
        daemon=True
    )
    thread.start()
    
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    mode_text = "♾️ CONTINUOUS MODE" if current_settings['continuous_mode'] else "📊 LIMITED MODE"
    
    bot.send_message(message.chat.id,
        f"🚀 <b>SPAM STARTED!</b>\n\n"
        f"{mode_text}\n\n"
        f"🎯 <b>Target:</b> {current_settings['target']}\n"
        f"🔗 <b>Thread ID:</b> <code>{thread_id}</code>\n"
        f"📊 <b>Messages:</b> {len(custom_messages)}\n"
        f"👥 <b>Sessions:</b> {valid_sessions}\n"
        f"⏱️ <b>Delay:</b> {current_settings['delay_min']}-{current_settings['delay_max']}s\n\n"
        f"<i>Spamming will continue until you stop it with /stop_spam</i>"
    )

def continuous_spam_worker(chat_id, thread_id, user_id):
    """CONTINUOUS SPAM WORKER - runs until stopped"""
    global spam_active, success_count, unsuccess_count, current_settings
    
    def check_access():
        if user_id == ADMIN_USER_ID:
            return True
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
    bot.send_message(chat_id, "🧪 Testing connection...")
    
    test_session = valid_sessions[0]
    test_msg = random.choice(custom_messages) if custom_messages else "Test message"
    formatted_msg = test_msg.replace("{target}", current_settings['target'])
    
    success, result = send_instagram_dm(
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
    
    # MAIN CONTINUOUS LOOP - runs until spam_active becomes False
    message_counter = 0
    
    while spam_active:
        try:
            # Check access every 10 messages
            if message_counter % 10 == 0 and not check_access():
                spam_active = False
                bot.send_message(chat_id, "⏰ <b>Access expired!</b>")
                break
            
            # Get message
            msg = random.choice(custom_messages)
            formatted_msg = msg.replace("{target}", current_settings['target'])
            
            # Get session (round-robin)
            session = valid_sessions[session_index % len(valid_sessions)]
            session_id = session.get('session_id')
            username = session.get('username', 'Account')
            
            # Send message
            success, result = send_instagram_dm(session_id, thread_id, formatted_msg)
            
            message_counter += 1
            current_settings['messages_sent'] += 1
            
            if success:
                with counter_lock:
                    success_count += 1
                status = "✅"
            else:
                with counter_lock:
                    unsuccess_count += 1
                status = "❌"
            
            # Show progress every 10 messages
            if message_counter % 10 == 0:
                total = success_count + unsuccess_count
                rate = (success_count/total*100) if total > 0 else 0
                
                bot.send_message(chat_id,
                    f"📊 <b>Progress Report</b>\n\n"
                    f"✅ <b>Total Sent:</b> {message_counter} messages\n"
                    f"✅ <b>Success:</b> {success_count}\n"
                    f"❌ <b>Failed:</b> {unsuccess_count}\n"
                    f"📈 <b>Rate:</b> {rate:.1f}%\n"
                    f"👥 <b>Using:</b> {username}\n\n"
                    f"<i>Spam is running... Send /stop_spam to stop</i>",
                    disable_notification=True
                )
            
            # Show every 50th message
            elif message_counter % 50 == 0:
                bot.send_message(chat_id,
                    f"🎉 <b>Milestone:</b> {message_counter} messages sent!\n"
                    f"Continuing spam...",
                    disable_notification=True
                )
            
            # Next session
            session_index += 1
            
            # Random delay between messages
            delay = random.uniform(current_settings['delay_min'], current_settings['delay_max'])
            time.sleep(delay)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(5)  # Wait longer on error
    
    # Spam stopped
    spam_active = False
    
    # Final report
    total = success_count + unsuccess_count
    rate = (success_count/total*100) if total > 0 else 0
    
    final_report = f"""
🛑 <b>SPAM STOPPED!</b>

📊 <b>Final Statistics:</b>

• ✅ Total Success: {success_count}
• ❌ Total Failed: {unsuccess_count}
• 📈 Success Rate: {rate:.1f}%
• 📤 Total Sent: {message_counter} messages

🎯 <b>Target:</b> {current_settings['target']}
🔗 <b>Thread:</b> {thread_id}

<i>Spam has been stopped.</i>
"""
    
    bot.send_message(chat_id, final_report)

@bot.message_handler(commands=['stop_spam'])
def stop_spam_command(message):
    """🛑 STOP SPAM"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "stop_spam"):
        return
    
    global spam_active
    
    if not spam_active:
        bot.send_message(message.chat.id, "⚠️ No spam running!")
        return
    
    spam_active = False
    bot.send_message(message.chat.id, 
        "🛑 <b>Stopping spam...</b>\n\n"
        "<i>Current message will finish, then spam will stop.</i>"
    )

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Statistics"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "stats"):
        return
    
    total = success_count + unsuccess_count
    rate = (success_count/total*100) if total > 0 else 0
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    stats_text = f"""
📊 <b>STATISTICS</b>

✅ <b>Success:</b> {success_count}
❌ <b>Failed:</b> {unsuccess_count}
📈 <b>Rate:</b> {rate:.1f}%

💬 <b>Messages:</b> {len(custom_messages)}
👥 <b>Sessions:</b> {valid_sessions}/{len(instagram_sessions)}

🎯 <b>Target:</b> {current_settings['target']}
🔗 <b>URL:</b> {'✅ Set' if current_settings['dm_url'] else '❌ Not set'}

⏱️ <b>Delay:</b> {current_settings['delay_min']}-{current_settings['delay_max']}s
♾️ <b>Mode:</b> {'CONTINUOUS' if current_settings['continuous_mode'] else 'LIMITED'}

📤 <b>Total Sent:</b> {current_settings['messages_sent']} messages

🔴 <b>Status:</b> {'🟢 RUNNING' if spam_active else '🔴 STOPPED'}
"""
    
    bot.send_message(message.chat.id, stats_text)

# ========== ADMIN COMMANDS ==========
@bot.message_handler(commands=['admin'])
def admin_command(message):
    """Admin panel"""
    user_id = message.from_user.id
    
    # FORCE ADMIN ACCESS
    if user_id != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    admin_text = f"""
🔐 <b>ADMIN PANEL</b>

✅ <b>Welcome Admin!</b>
🆔 <b>ID:</b> <code>{user_id}</code>

📊 <b>Statistics:</b>
• Users: {len(user_manager.get_all_users())}
• Active: {len(user_manager.get_active_users())}
• Messages: {len(custom_messages)}
• Sessions: {len(instagram_sessions)}
• Spam: {'🟢 Running' if spam_active else '🔴 Stopped'}

⚙️ <b>Commands:</b>
• /users - View all users
• /broadcast [msg] - Broadcast
• /addtime [id] [amt] [unit] - Add time
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="👥 Users", callback_data="admin_users"),
        InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats")
    )
    keyboard.add(
        InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="⏰ Add Time", callback_data="admin_addtime_menu")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, admin_text, reply_markup=keyboard)

@bot.message_handler(commands=['users'])
def users_command(message):
    """View users"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    users = user_manager.get_all_users()
    if not users:
        bot.send_message(message.chat.id, "📭 No users!")
        return
    
    response = "👥 <b>USERS:</b>\n\n"
    
    for uid, data in users.items():
        username = data.get('username', 'Unknown')
        is_admin = "🛡️ ADMIN" if data.get('is_admin') else "👤 User"
        plan = data.get('plan', 'Free')
        
        response += f"{is_admin}\n"
        response += f"ID: <code>{uid}</code>\n"
        response += f"Name: {username}\n"
        response += f"Plan: {plan}\n"
        response += "─" * 20 + "\n\n"
    
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    """Broadcast"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_USER_ID:
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
        
        bot.send_message(message.chat.id, f"📢 Sending...")
        
        for uid in users.keys():
            try:
                bot.send_message(int(uid), 
                    f"📢 <b>ANNOUNCEMENT:</b>\n\n"
                    f"{broadcast_msg}"
                )
                sent += 1
                time.sleep(0.1)
            except:
                failed += 1
        
        bot.send_message(message.chat.id, 
            f"✅ <b>Done!</b>\n"
            f"✅ Sent: {sent}\n"
            f"❌ Failed: {failed}"
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['addtime'])
def addtime_command(message):
    """Add time"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_USER_ID:
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
            bot.send_message(message.chat.id, "❌ User not found!")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

# ========== CALLBACK HANDLERS ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    """Handle callbacks"""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    print(f"\nCallback: {user_id} clicked {call.data}")
    
    # Register user
    username = call.from_user.username or call.from_user.first_name or "User"
    user_manager.add_user(user_id, username)
    
    # Check access
    if user_id != ADMIN_USER_ID:
        has_access, message = user_manager.check_access(user_id)
        if not has_access:
            if "expired" in message.lower():
                bot.send_message(chat_id,
                    f"⏰ <b>ACCESS EXPIRED!</b>\n\n"
                    f"Contact {CONTACT_USERNAME} for paid access."
                )
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
    
    elif call.data == "toggle_mode":
        # Toggle between continuous and limited mode
        current_settings['continuous_mode'] = not current_settings['continuous_mode']
        mode_text = "CONTINUOUS" if current_settings['continuous_mode'] else "LIMITED"
        bot.send_message(chat_id, f"✅ Mode set to: {mode_text}")
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
        msg = bot.send_message(chat_id, "🔗 Enter Instagram DM URL or Thread ID:")
        bot.register_next_step_handler(msg, process_url)
    
    elif call.data == "set_delay":
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(text="⚡ 1-2s (FAST)", callback_data="delay_1_2"),
            InlineKeyboardButton(text="🚀 2-3s (MEDIUM)", callback_data="delay_2_3")
        )
        keyboard.add(
            InlineKeyboardButton(text="💨 3-5s (SLOW)", callback_data="delay_3_5"),
            InlineKeyboardButton(text="🐢 5-10s (SAFE)", callback_data="delay_5_10")
        )
        bot.send_message(chat_id, "⏱️ Select delay:", reply_markup=keyboard)
    
    elif call.data.startswith("delay_"):
        delays = call.data.split("_")[1:]
        current_settings['delay_min'] = float(delays[0])
        current_settings['delay_max'] = float(delays[1])
        bot.send_message(chat_id, f"✅ Delay: {delays[0]}-{delays[1]}s")

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
        else:
            bot.send_message(message.chat.id, "❌ User not found!")
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
            f"✅ <b>URL set!</b>\n"
            f"Thread ID: <code>{thread_id}</code>"
        )
    else:
        current_settings['dm_url'] = url
        bot.send_message(message.chat.id, 
            "⚠️ <b>URL saved</b>\n"
            "No thread ID detected. Make sure URL is correct."
        )

# ========== MAIN ==========
if __name__ == "__main__":
    print(f"""
╔════════════════════════════════════════════╗
║     INSTAGRAM CONTINUOUS SPAM BOT         ║
║     RUNS UNTIL YOU STOP IT               ║
╚════════════════════════════════════════════╝
    """)
    
    print(f"🔑 ADMIN ID: {ADMIN_USER_ID}")
    print(f"🤖 Bot: {BOT_USERNAME}")
    print(f"💬 Messages: {len(custom_messages)}")
    print(f"🔑 Sessions: {len(instagram_sessions)}")
    print(f"♾️ Mode: {'CONTINUOUS' if current_settings['continuous_mode'] else 'LIMITED'}")
    
    try:
        bot_info = bot.get_me()
        print(f"\n✅ Bot: @{bot_info.username}")
        print("✅ Bot ready!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("⚠️ IMPORTANT:")
    print(f"• Continuous spam mode enabled")
    print(f"• Spam runs until you send /stop_spam")
    print(f"• Admin can add time to users")
    print("="*60 + "\n")
    
    print("🚀 Starting bot...")
    bot.infinity_polling()
