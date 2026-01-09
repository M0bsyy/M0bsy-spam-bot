import os
import sys
import json
import random
import time
import threading
import requests
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ========== CONFIGURATION ==========
TELEGRAM_BOT_TOKEN = "8595686704:AAGZ6-f7cjiaET1J2yXM-QBuJCq_fyOMJ7o"
ADMIN_USER_ID = 6107382622  # Your Telegram User ID
BOT_USERNAME = "@M0bsy_spam_bot"
CONTACT_USERNAME = "@M0bsy_olds"

# Initialize bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# ========== INSTAGRAM API FUNCTIONS ==========
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
        return False, None, f"❌ Error: {str(e)}"

def send_instagram_dm(session_id, thread_id, message):
    """Send Instagram DM"""
    try:
        # Get CSRF token
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
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
        
        # Updated headers
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
        
        data = {
            'action': 'send_item',
            'client_context': client_context,
            'device_id': f"android-{hashlib.md5(str(time.time()).encode()).hexdigest()[:16]}",
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
        else:
            return False, f"❌ HTTP {response.status_code}: {response.text[:100]}"
            
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

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
        self.users_file = Path("users.json")
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
        
        # Create or update user
        if user_id_str not in self.users:
            # New user
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
        else:
            # Update existing user
            if is_admin:
                self.users[user_id_str]["is_admin"] = True
                self.users[user_id_str]["plan"] = "lifetime_admin"
                self.users[user_id_str]["expiry"] = (datetime.now() + timedelta(days=36500)).isoformat()
                self.users[user_id_str]["active"] = True
            self.users[user_id_str]["username"] = username
        
        self.save_users()
        return True
    
    def check_access(self, user_id: int):
        """Check if user has access"""
        user_id_str = str(user_id)
        
        # Admin always has access
        if user_id == ADMIN_USER_ID:
            return True, "✅ Admin access"
        
        if user_id_str not in self.users:
            return False, "❌ User not registered"
        
        user_data = self.users[user_id_str]
        
        # Check if active
        if not user_data.get("active", True):
            return False, "❌ Account deactivated"
        
        # Check expiry
        expiry_str = user_data.get("expiry", "")
        if not expiry_str:
            return False, "❌ No expiry date"
        
        try:
            expiry = datetime.fromisoformat(expiry_str)
            if datetime.now() > expiry:
                user_data["active"] = False
                self.save_users()
                return False, "❌ Trial expired"
            
            return True, "✅ Access granted"
            
        except:
            return False, "❌ Error checking access"
    
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
    "continuous_mode": True,
    "messages_sent": 0
}

# ========== DATA MANAGEMENT ==========
DATA_DIR = Path("bot_data")
DATA_DIR.mkdir(exist_ok=True)
MESSAGES_FILE = DATA_DIR / "messages.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

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

def save_settings():
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(current_settings, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_settings():
    global current_settings
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                current_settings.update(json.load(f))
    except:
        pass

# Load data
load_messages()
load_sessions()
load_settings()

# ========== INITIALIZE ==========
user_manager = UserManager()

def initialize_admin():
    """Initialize admin account"""
    print(f"\n{'='*60}")
    print(f"🤖 INSTAGRAM SPAM BOT")
    print(f"🔑 ADMIN ID: {ADMIN_USER_ID}")
    print(f"🤖 Bot: {BOT_USERNAME}")
    print(f"{'='*60}\n")
    
    # Add admin to user manager
    user_manager.add_user(ADMIN_USER_ID, "ADMIN")
    print(f"✅ Admin initialized: {ADMIN_USER_ID}")

initialize_admin()

# ========== HELPER FUNCTIONS ==========
def check_user_access(chat_id, user_id, command_name=""):
    """Check if user has access to use bot"""
    user_id_str = str(user_id)
    
    # Auto-register user if not exists
    if user_id_str not in user_manager.users:
        username = f"User_{user_id}"
        user_manager.add_user(user_id, username)
    
    # Admin always has access
    if user_id == ADMIN_USER_ID:
        return True
    
    # Check regular users
    has_access, message = user_manager.check_access(user_id)
    
    if not has_access:
        if "expired" in message.lower():
            bot.send_message(chat_id,
                f"⏰ <b>ACCESS EXPIRED!</b>\n\n"
                f"Your trial period has ended.\n"
                f"Contact {CONTACT_USERNAME} for paid access."
            )
        else:
            bot.send_message(chat_id, f"{message}")
        return False
    
    return True

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_manager.is_admin(user_id)

# ========== BASIC COMMANDS ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or "User"
    
    print(f"\n[START] User {user_id} ({username})")
    
    # Add user to system
    user_manager.add_user(user_id, username)
    
    # Send welcome message
    is_admin_user = is_admin(user_id)
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    welcome_text = f"""
╔════════════════════════════════════════════╗
║     INSTAGRAM SPAM BOT v3.0              ║
║     CONTINUOUS SPAM MODE                 ║
╚════════════════════════════════════════════╝

👤 <b>User ID:</b> <code>{user_id}</code>
{'🛡️ <b>Status:</b> ✅ ADMIN (Lifetime Access)' if is_admin_user else '👤 <b>Status:</b> Trial User'}

📋 <b>Available Commands:</b>
/start - Show this menu
/addmsg - Add spam message
/listmsg - List all messages
/addsession - Add Instagram session
/sessions - View all sessions
/setup - Configure spam settings
/start_spam - 🚀 Start continuous spam
/stop_spam - 🛑 Stop spam
/stats - View statistics

{'🔸 <b>Admin Commands:</b>' if is_admin_user else ''}
{'• /admin - Admin control panel' if is_admin_user else ''}
{'• /users - View all users' if is_admin_user else ''}
{'• /broadcast - Send message to all users' if is_admin_user else ''}
{'• /addtime - Add time to user' if is_admin_user else ''}

📊 <b>Current Status:</b>
• Messages: {len(custom_messages)}
• Valid Sessions: {valid_sessions}
• Target: {current_settings['target']}
• Spam: {'🟢 RUNNING' if spam_active else '🔴 STOPPED'}
• Mode: {'♾️ CONTINUOUS' if current_settings['continuous_mode'] else '📊 LIMITED'}
• Total Sent: {current_settings['messages_sent']} messages
"""
    
    # Create keyboard
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("➕ Add Message", callback_data="add_msg"),
        InlineKeyboardButton("🔑 Add Session", callback_data="add_session")
    )
    keyboard.row(
        InlineKeyboardButton("📋 Messages", callback_data="list_msg"),
        InlineKeyboardButton("👥 Sessions", callback_data="list_sessions")
    )
    keyboard.row(
        InlineKeyboardButton("⚙️ Setup", callback_data="setup"),
        InlineKeyboardButton("🚀 Start Spam", callback_data="start_spam")
    )
    keyboard.row(
        InlineKeyboardButton("🛑 Stop Spam", callback_data="stop_spam"),
        InlineKeyboardButton("📊 Stats", callback_data="stats")
    )
    
    if is_admin_user:
        keyboard.row(
            InlineKeyboardButton("🔐 ADMIN PANEL", callback_data="admin_panel")
        )
    
    bot.send_message(message.chat.id, welcome_text, reply_markup=keyboard)

@bot.message_handler(commands=['addmsg'])
def addmsg_command(message):
    """Add spam message"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "addmsg"):
        return
    
    bot.send_message(message.chat.id, 
        "✍️ <b>Send your spam message:</b>\n\n"
        "Use <code>{target}</code> to insert the target username\n"
        "Example: Hello {target}! How are you? 👋"
    )
    bot.register_next_step_handler(message, process_new_message)

def process_new_message(message):
    """Process new message"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "addmsg"):
        return
    
    new_message = message.text.strip()
    if not new_message:
        bot.send_message(message.chat.id, "❌ Message cannot be empty!")
        return
    
    custom_messages.append(new_message)
    save_messages()
    
    bot.send_message(message.chat.id, 
        f"✅ <b>Message added successfully!</b>\n\n"
        f"Total messages: {len(custom_messages)}"
    )

@bot.message_handler(commands=['listmsg'])
def listmsg_command(message):
    """List all spam messages"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "listmsg"):
        return
    
    if not custom_messages:
        bot.send_message(message.chat.id, "📭 No messages found!")
        return
    
    response = "📋 <b>AVAILABLE MESSAGES:</b>\n\n"
    
    for i, msg in enumerate(custom_messages, 1):
        preview = msg[:50] + "..." if len(msg) > 50 else msg
        response += f"{i}. <code>{preview}</code>\n\n"
    
    response += f"📊 <b>Total:</b> {len(custom_messages)} messages"
    
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['addsession'])
def addsession_command(message):
    """Add Instagram session"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "addsession"):
        return
    
    instruction = """
🔑 <b>HOW TO GET INSTAGRAM SESSION ID:</b>

1. Open Instagram in Chrome/Firefox
2. Login to your Instagram account
3. Press <code>F12</code> to open Developer Tools
4. Go to <b>Application</b> tab
5. Click on <b>Cookies</b> → <b>https://www.instagram.com</b>
6. Find <b>sessionid</b> cookie
7. Copy the <b>Value</b>

📝 <b>Send the sessionid value:</b>
"""
    
    bot.send_message(message.chat.id, instruction)
    bot.register_next_step_handler(message, process_new_session)

def process_new_session(message):
    """Process new Instagram session"""
    user_id = message.from_user.id
    
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
            "added": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "last_used": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        instagram_sessions.append(session_data)
        save_sessions()
        
        bot.send_message(message.chat.id, 
            f"✅ <b>Session added successfully!</b>\n\n"
            f"👤 <b>Username:</b> {username}\n"
            f"🕒 <b>Added:</b> {datetime.now().strftime('%H:%M:%S')}\n"
            f"📊 <b>Valid sessions:</b> {len([s for s in instagram_sessions if s.get('status') == 'valid'])}"
        )
    else:
        bot.send_message(message.chat.id, 
            f"❌ <b>Session validation failed!</b>\n\n"
            f"Reason: {info}\n\n"
            "Make sure:\n"
            "1. Session ID is correct\n"
            "2. Instagram account is logged in\n"
            "3. Session is not expired"
        )

@bot.message_handler(commands=['sessions'])
def sessions_command(message):
    """View all Instagram sessions"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "sessions"):
        return
    
    if not instagram_sessions:
        bot.send_message(message.chat.id, "🔐 No sessions found!")
        return
    
    valid_sessions = [s for s in instagram_sessions if s.get('status') == 'valid']
    
    response = "👥 <b>INSTAGRAM SESSIONS:</b>\n\n"
    
    if valid_sessions:
        response += "✅ <b>VALID SESSIONS:</b>\n"
        for i, session in enumerate(valid_sessions, 1):
            username = session.get('username', 'Unknown')
            added = session.get('added', 'Unknown')
            response += f"{i}. <b>{username}</b>\n"
            response += f"   Added: {added}\n\n"
    
    response += f"📊 <b>Statistics:</b>\n"
    response += f"• Valid: {len(valid_sessions)}\n"
    response += f"• Total: {len(instagram_sessions)}"
    
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['setup'])
def setup_command(message):
    """Setup spam configuration"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "setup"):
        return
    
    current_config = f"""
⚙️ <b>SPAM CONFIGURATION:</b>

🎯 <b>Target Username:</b> {current_settings['target']}
🔗 <b>Instagram URL:</b> {'✅ Set' if current_settings['dm_url'] else '❌ Not set'}
⏱️ <b>Delay Between Messages:</b> {current_settings['delay_min']}-{current_settings['delay_max']} seconds
♾️ <b>Spam Mode:</b> {'CONTINUOUS' if current_settings['continuous_mode'] else 'LIMITED'}
📊 <b>Messages Sent:</b> {current_settings['messages_sent']}
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("🎯 Set Target", callback_data="set_target"),
        InlineKeyboardButton("🔗 Set URL", callback_data="set_url")
    )
    keyboard.row(
        InlineKeyboardButton("⏱️ Set Delay", callback_data="set_delay"),
        InlineKeyboardButton("♾️ Toggle Mode", callback_data="toggle_mode")
    )
    keyboard.row(
        InlineKeyboardButton("◀️ Back to Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, current_config + "\n<b>Select an option:</b>", reply_markup=keyboard)

@bot.message_handler(commands=['start_spam'])
def start_spam_command(message):
    """Start continuous spam"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "start_spam"):
        return
    
    # Check requirements
    if not custom_messages:
        bot.send_message(message.chat.id, 
            "❌ <b>No messages found!</b>\n\n"
            "Add messages first using /addmsg"
        )
        return
    
    valid_sessions = [s for s in instagram_sessions if s.get('status') == 'valid']
    if not valid_sessions:
        bot.send_message(message.chat.id, 
            "❌ <b>No valid sessions found!</b>\n\n"
            "Add Instagram sessions first using /addsession"
        )
        return
    
    if not current_settings['dm_url']:
        bot.send_message(message.chat.id, 
            "❌ <b>No Instagram URL set!</b>\n\n"
            "Set the target URL first using /setup"
        )
        return
    
    thread_id = get_thread_id_from_url(current_settings['dm_url'])
    if not thread_id:
        bot.send_message(message.chat.id, 
            "❌ <b>Invalid URL format!</b>\n\n"
            "Correct formats:\n"
            "• https://www.instagram.com/direct/t/THREAD_ID/\n"
            "• Direct thread ID: 17850716417587515\n\n"
            "Use /setup to set the correct URL"
        )
        return
    
    global spam_active
    
    if spam_active:
        bot.send_message(message.chat.id, "⚠️ Spam is already running!")
        return
    
    # Start spam in separate thread
    spam_active = True
    thread = threading.Thread(
        target=spam_worker,
        args=(message.chat.id, thread_id, user_id),
        daemon=True
    )
    thread.start()
    
    mode_text = "♾️ CONTINUOUS MODE" if current_settings['continuous_mode'] else "📊 LIMITED MODE"
    
    bot.send_message(message.chat.id,
        f"🚀 <b>SPAM STARTED SUCCESSFULLY!</b>\n\n"
        f"{mode_text}\n\n"
        f"🎯 <b>Target:</b> {current_settings['target']}\n"
        f"🔗 <b>Thread ID:</b> <code>{thread_id}</code>\n"
        f"📊 <b>Messages:</b> {len(custom_messages)}\n"
        f"👥 <b>Sessions:</b> {len(valid_sessions)}\n"
        f"⏱️ <b>Delay:</b> {current_settings['delay_min']}-{current_settings['delay_max']}s\n\n"
        f"<i>Spam will continue until you stop it with /stop_spam</i>"
    )

def spam_worker(chat_id, thread_id, user_id):
    """Worker function for spam"""
    global spam_active, success_count, unsuccess_count, current_settings
    
    def check_user_access_in_thread():
        """Check access inside thread"""
        if user_id == ADMIN_USER_ID:
            return True
        has_access, _ = user_manager.check_access(user_id)
        return has_access
    
    # Get valid sessions
    valid_sessions = [s for s in instagram_sessions if s.get('status') == 'valid']
    if not valid_sessions:
        bot.send_message(chat_id, "❌ No valid sessions available!")
        spam_active = False
        return
    
    # Check user access
    if not check_user_access_in_thread():
        bot.send_message(chat_id, "❌ Access denied!")
        spam_active = False
        return
    
    # Test connection
    bot.send_message(chat_id, "🧪 Testing connection...")
    
    test_session = valid_sessions[0]
    test_msg = random.choice(custom_messages) if custom_messages else "Test message"
    formatted_msg = test_msg.replace("{target}", current_settings['target'])
    
    success, result = send_instagram_dm(
        test_session.get('session_id'), 
        thread_id, 
        formatted_msg
    )
    
    bot.send_message(chat_id, f"🧪 <b>Test Result:</b> {result}")
    
    if not success:
        bot.send_message(chat_id, 
            "⚠️ <b>Connection test failed!</b>\n\n"
            "Possible issues:\n"
            "1. Session expired\n"
            "2. Invalid thread ID\n"
            "3. Instagram rate limiting\n"
            "4. Account blocked\n\n"
            "Check your configuration and try again."
        )
        spam_active = False
        return
    
    # Main spam loop
    message_counter = 0
    session_index = 0
    
    while spam_active:
        try:
            # Check access every 10 messages
            if message_counter % 10 == 0 and not check_user_access_in_thread():
                spam_active = False
                bot.send_message(chat_id, "⏰ <b>Access expired!</b>")
                break
            
            # Get random message
            msg = random.choice(custom_messages)
            formatted_msg = msg.replace("{target}", current_settings['target'])
            
            # Get session (round-robin)
            session = valid_sessions[session_index % len(valid_sessions)]
            session_id = session.get('session_id')
            username = session.get('username', 'Unknown Account')
            
            # Send message
            success, result = send_instagram_dm(session_id, thread_id, formatted_msg)
            
            message_counter += 1
            current_settings['messages_sent'] += 1
            save_settings()
            
            if success:
                with counter_lock:
                    success_count += 1
            else:
                with counter_lock:
                    unsuccess_count += 1
            
            # Update session last used
            session['last_used'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            save_sessions()
            
            # Show progress every 10 messages
            if message_counter % 10 == 0:
                total = success_count + unsuccess_count
                success_rate = (success_count / total * 100) if total > 0 else 0
                
                progress_msg = f"""
📊 <b>SPAM PROGRESS</b>

✅ <b>Messages Sent:</b> {message_counter}
✅ <b>Successful:</b> {success_count}
❌ <b>Failed:</b> {unsuccess_count}
📈 <b>Success Rate:</b> {success_rate:.1f}%
👥 <b>Current Session:</b> {username}

<i>Spam is running... Send /stop_spam to stop</i>
"""
                bot.send_message(chat_id, progress_msg, disable_notification=True)
            
            # Next session
            session_index += 1
            
            # Delay between messages
            delay = random.uniform(current_settings['delay_min'], current_settings['delay_max'])
            time.sleep(delay)
            
        except Exception as e:
            print(f"[ERROR] Spam worker: {e}")
            time.sleep(5)
    
    # Spam stopped
    spam_active = False
    
    # Final report
    total = success_count + unsuccess_count
    success_rate = (success_count / total * 100) if total > 0 else 0
    
    final_report = f"""
🛑 <b>SPAM STOPPED</b>

📊 <b>FINAL STATISTICS:</b>

✅ <b>Successful Messages:</b> {success_count}
❌ <b>Failed Messages:</b> {unsuccess_count}
📈 <b>Success Rate:</b> {success_rate:.1f}%
📤 <b>Total Sent:</b> {message_counter} messages

🎯 <b>Target:</b> {current_settings['target']}
🔗 <b>Thread ID:</b> {thread_id}

<i>Spam has been successfully stopped.</i>
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
        bot.send_message(message.chat.id, "⚠️ No spam is currently running!")
        return
    
    spam_active = False
    bot.send_message(message.chat.id, 
        "🛑 <b>Stopping spam...</b>\n\n"
        "<i>Current operation will finish, then spam will stop.</i>"
    )

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Show statistics"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "stats"):
        return
    
    total = success_count + unsuccess_count
    success_rate = (success_count / total * 100) if total > 0 else 0
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    stats_text = f"""
📊 <b>BOT STATISTICS</b>

✅ <b>Successful Messages:</b> {success_count}
❌ <b>Failed Messages:</b> {unsuccess_count}
📈 <b>Success Rate:</b> {success_rate:.1f}%

💬 <b>Messages Available:</b> {len(custom_messages)}
👥 <b>Valid Sessions:</b> {valid_sessions}/{len(instagram_sessions)}

🎯 <b>Target:</b> {current_settings['target']}
🔗 <b>URL Set:</b> {'✅ Yes' if current_settings['dm_url'] else '❌ No'}

⏱️ <b>Delay:</b> {current_settings['delay_min']}-{current_settings['delay_max']}s
♾️ <b>Mode:</b> {'CONTINUOUS' if current_settings['continuous_mode'] else 'LIMITED'}

📤 <b>Total Messages Sent:</b> {current_settings['messages_sent']}

🔴 <b>Status:</b> {'🟢 RUNNING' if spam_active else '🔴 STOPPED'}
"""
    
    bot.send_message(message.chat.id, stats_text)

# ========== ADMIN COMMANDS ==========
@bot.message_handler(commands=['admin'])
def admin_command(message):
    """Admin panel"""
    user_id = message.from_user.id
    
    print(f"[ADMIN] Request from user: {user_id}")
    
    # Check if admin
    if user_id != ADMIN_USER_ID:
        print(f"[ADMIN] Access denied for user: {user_id}")
        bot.send_message(message.chat.id, 
            "❌ <b>Access Denied!</b>\n\n"
            "This command is for administrators only."
        )
        return
    
    print(f"[ADMIN] Access granted for user: {user_id}")
    
    admin_text = f"""
🔐 <b>ADMINISTRATOR PANEL</b>

✅ <b>Welcome Admin!</b>
🆔 <b>Your ID:</b> <code>{user_id}</code>
🤖 <b>Bot:</b> {BOT_USERNAME}

📊 <b>SYSTEM STATISTICS:</b>
• Total Users: {len(user_manager.get_all_users())}
• Active Users: {len(user_manager.get_active_users())}
• Messages: {len(custom_messages)}
• Instagram Sessions: {len(instagram_sessions)}
• Spam Status: {'🟢 RUNNING' if spam_active else '🔴 STOPPED'}

⚙️ <b>ADMIN COMMANDS:</b>
• /users - View all registered users
• /broadcast [message] - Broadcast message to all users
• /addtime [user_id] [amount] [unit] - Add time to user account
• /stats - Detailed bot statistics

💡 <b>Quick Actions:</b>
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("👥 View All Users", callback_data="admin_users"),
        InlineKeyboardButton("📊 System Stats", callback_data="admin_stats")
    )
    keyboard.row(
        InlineKeyboardButton("📢 Send Broadcast", callback_data="admin_broadcast"),
        InlineKeyboardButton("⏰ Add User Time", callback_data="admin_addtime")
    )
    keyboard.row(
        InlineKeyboardButton("◀️ Main Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, admin_text, reply_markup=keyboard)

@bot.message_handler(commands=['users'])
def users_command(message):
    """View all users"""
    user_id = message.from_user.id
    
    # Check if admin
    if user_id != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    users = user_manager.get_all_users()
    if not users:
        bot.send_message(message.chat.id, "📭 No users found!")
        return
    
    response = f"👥 <b>TOTAL USERS: {len(users)}</b>\n\n"
    
    for uid, data in users.items():
        username = data.get('username', 'Unknown')
        is_admin = "🛡️ ADMIN" if data.get('is_admin') else "👤 USER"
        plan = data.get('plan', 'Trial')
        active = "✅ Active" if data.get('active') else "❌ Inactive"
        expiry = data.get('expiry', 'Unknown')
        
        response += f"{is_admin} - {active}\n"
        response += f"ID: <code>{uid}</code>\n"
        response += f"Username: {username}\n"
        response += f"Plan: {plan}\n"
        
        try:
            expiry_date = datetime.fromisoformat(expiry)
            if data.get('is_admin'):
                expiry_str = "LIFETIME"
            else:
                expiry_str = expiry_date.strftime("%Y-%m-%d %H:%M")
            response += f"Expires: {expiry_str}\n"
        except:
            response += f"Expires: {expiry}\n"
        
        response += "─" * 30 + "\n\n"
    
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    """Broadcast message to all users"""
    user_id = message.from_user.id
    
    # Check if admin
    if user_id != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    try:
        # Extract message text
        if message.reply_to_message:
            broadcast_msg = message.reply_to_message.text or message.reply_to_message.caption
        else:
            parts = message.text.split(' ', 1)
            if len(parts) < 2:
                bot.send_message(message.chat.id, 
                    "Usage: /broadcast [message]\n"
                    "or reply /broadcast to a message"
                )
                return
            broadcast_msg = parts[1]
        
        if not broadcast_msg:
            bot.send_message(message.chat.id, "❌ Message cannot be empty!")
            return
        
        users = user_manager.get_active_users()
        
        if not users:
            bot.send_message(message.chat.id, "❌ No active users found!")
            return
        
        sent = 0
        failed = 0
        
        bot.send_message(message.chat.id, f"📢 Broadcasting to {len(users)} users...")
        
        for uid in users.keys():
            try:
                bot.send_message(int(uid), 
                    f"📢 <b>ANNOUNCEMENT FROM ADMIN</b>\n\n"
                    f"{broadcast_msg}\n\n"
                    f"<i>Sent via {BOT_USERNAME}</i>"
                )
                sent += 1
                time.sleep(0.1)  # Prevent rate limiting
            except Exception as e:
                print(f"Failed to send to {uid}: {e}")
                failed += 1
        
        bot.send_message(message.chat.id, 
            f"✅ <b>Broadcast Complete!</b>\n\n"
            f"✅ Successfully sent: {sent}\n"
            f"❌ Failed: {failed}\n"
            f"📊 Total users: {len(users)}"
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['addtime'])
def addtime_command(message):
    """Add time to user account"""
    user_id = message.from_user.id
    
    # Check if admin
    if user_id != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 4:
            bot.send_message(message.chat.id, 
                "Usage: /addtime [user_id] [amount] [unit]\n\n"
                "<b>Available units:</b>\n"
                "• minutes - Add minutes\n"
                "• hours - Add hours\n"
                "• days - Add days\n"
                "• weeks - Add weeks\n"
                "• months - Add months\n"
                "• lifetime - Lifetime access\n\n"
                "<b>Examples:</b>\n"
                "/addtime 123456789 7 days\n"
                "/addtime 123456789 1 lifetime"
            )
            return
        
        target_user_id = int(parts[1])
        amount = int(parts[2])
        unit = parts[3].lower()
        
        valid_units = ["minutes", "hours", "days", "weeks", "months", "lifetime"]
        if unit not in valid_units:
            bot.send_message(message.chat.id, 
                f"❌ Invalid unit!\n\n"
                f"Valid units: {', '.join(valid_units)}"
            )
            return
        
        if user_manager.add_user_time(target_user_id, amount, unit):
            if unit == "lifetime":
                time_msg = "LIFETIME access"
            else:
                time_msg = f"{amount} {unit}"
            
            # Notify admin
            bot.send_message(message.chat.id, 
                f"✅ <b>Time added successfully!</b>\n\n"
                f"User ID: <code>{target_user_id}</code>\n"
                f"Added: {time_msg}"
            )
            
            # Try to notify user
            try:
                bot.send_message(target_user_id, 
                    f"🎉 <b>ACCOUNT UPDATED!</b>\n\n"
                    f"Admin has added {time_msg} to your account.\n"
                    f"Your access has been extended!\n\n"
                    f"Thank you for using our service! 🚀"
                )
            except:
                pass
        else:
            bot.send_message(message.chat.id, 
                "❌ User not found!\n"
                "Make sure the user ID is correct."
            )
    except ValueError:
        bot.send_message(message.chat.id, "❌ Invalid user ID! Must be a number.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

# ========== CALLBACK HANDLERS ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    """Handle inline keyboard callbacks"""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    print(f"\n[CALLBACK] User {user_id} clicked: {call.data}")
    
    # Check user access
    if user_id != ADMIN_USER_ID:
        has_access, access_msg = user_manager.check_access(user_id)
        if not has_access:
            bot.answer_callback_query(call.id, access_msg, show_alert=True)
            return
    
    bot.answer_callback_query(call.id)
    
    # Handle different callbacks
    if call.data == "main_menu":
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass
        send_start_message(call.message)
    
    elif call.data == "admin_panel":
        admin_command(call.message)
    
    elif call.data == "admin_users":
        users_command(call.message)
    
    elif call.data == "admin_stats":
        stats_command(call.message)
    
    elif call.data == "admin_broadcast":
        msg = bot.send_message(chat_id, 
            "📢 <b>Send broadcast message:</b>\n\n"
            "Enter the message you want to send to all users."
        )
        bot.register_next_step_handler(msg, lambda m: broadcast_from_callback(m, user_id))
    
    elif call.data == "admin_addtime":
        msg = bot.send_message(chat_id, 
            "⏰ <b>Add time to user:</b>\n\n"
            "Send in format:\n"
            "<code>user_id amount unit</code>\n\n"
            "Example:\n"
            "<code>123456789 7 days</code>\n\n"
            "Units: minutes, hours, days, weeks, months, lifetime"
        )
        bot.register_next_step_handler(msg, lambda m: addtime_from_callback(m, user_id))
    
    elif call.data == "add_msg":
        msg = bot.send_message(chat_id, "✍️ Send your spam message:")
        bot.register_next_step_handler(msg, process_new_message)
    
    elif call.data == "list_msg":
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass
        listmsg_command(call.message)
    
    elif call.data == "add_session":
        msg = bot.send_message(chat_id, "🔑 Send Instagram session ID:")
        bot.register_next_step_handler(msg, process_new_session)
    
    elif call.data == "list_sessions":
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass
        sessions_command(call.message)
    
    elif call.data == "setup":
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass
        setup_command(call.message)
    
    elif call.data == "toggle_mode":
        current_settings['continuous_mode'] = not current_settings['continuous_mode']
        mode_text = "CONTINUOUS" if current_settings['continuous_mode'] else "LIMITED"
        bot.send_message(chat_id, f"✅ Mode changed to: {mode_text}")
        setup_command(call.message)
    
    elif call.data == "start_spam":
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass
        start_spam_command(call.message)
    
    elif call.data == "stop_spam":
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass
        stop_spam_command(call.message)
    
    elif call.data == "stats":
        try:
            bot.delete_message(chat_id, message_id)
        except:
            pass
        stats_command(call.message)
    
    elif call.data == "set_target":
        msg = bot.send_message(chat_id, "🎯 Enter target username (used in {target}):")
        bot.register_next_step_handler(msg, process_target_setting)
    
    elif call.data == "set_url":
        msg = bot.send_message(chat_id, 
            "🔗 <b>Enter Instagram URL:</b>\n\n"
            "Supported formats:\n"
            "• Full URL: https://www.instagram.com/direct/t/THREAD_ID/\n"
            "• Thread ID only: 17850716417587515\n"
            "• DM link from Instagram app"
        )
        bot.register_next_step_handler(msg, process_url_setting)
    
    elif call.data == "set_delay":
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("⚡ 1-2s (Very Fast)", callback_data="delay_1_2"),
            InlineKeyboardButton("🚀 2-3s (Fast)", callback_data="delay_2_3")
        )
        keyboard.row(
            InlineKeyboardButton("🐇 3-5s (Normal)", callback_data="delay_3_5"),
            InlineKeyboardButton("🐢 5-10s (Safe)", callback_data="delay_5_10")
        )
        keyboard.row(
            InlineKeyboardButton("◀️ Back", callback_data="setup")
        )
        
        bot.edit_message_text(
            "⏱️ <b>Select delay between messages:</b>",
            chat_id, 
            message_id, 
            reply_markup=keyboard
        )
    
    elif call.data.startswith("delay_"):
        delays = call.data.split("_")[1:]
        if len(delays) == 2:
            current_settings['delay_min'] = float(delays[0])
            current_settings['delay_max'] = float(delays[1])
            save_settings()
            bot.send_message(chat_id, f"✅ Delay set to: {delays[0]}-{delays[1]} seconds")
            setup_command(call.message)

def broadcast_from_callback(message, user_id):
    """Handle broadcast from callback"""
    class FakeMessage:
        def __init__(self, text, user_id):
            self.text = text
            self.chat = type('obj', (object,), {'id': message.chat.id})
            self.from_user = type('obj', (object,), {'id': user_id})
    
    fake_msg = FakeMessage(f"/broadcast {message.text}", user_id)
    broadcast_command(fake_msg)

def addtime_from_callback(message, user_id):
    """Handle addtime from callback"""
    class FakeMessage:
        def __init__(self, text, user_id):
            self.text = text
            self.chat = type('obj', (object,), {'id': message.chat.id})
            self.from_user = type('obj', (object,), {'id': user_id})
    
    fake_msg = FakeMessage(f"/addtime {message.text}", user_id)
    addtime_command(fake_msg)

def process_target_setting(message):
    """Process target setting"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "setup"):
        return
    
    target = message.text.strip()
    if target:
        current_settings['target'] = target
        save_settings()
        bot.send_message(message.chat.id, f"✅ Target set to: {target}")
    else:
        bot.send_message(message.chat.id, "❌ Target cannot be empty!")

def process_url_setting(message):
    """Process URL setting"""
    user_id = message.from_user.id
    
    if not check_user_access(message.chat.id, user_id, "setup"):
        return
    
    url = message.text.strip()
    if not url:
        bot.send_message(message.chat.id, "❌ URL cannot be empty!")
        return
    
    thread_id = get_thread_id_from_url(url)
    
    if thread_id:
        current_settings['dm_url'] = url
        save_settings()
        bot.send_message(message.chat.id, 
            f"✅ <b>URL set successfully!</b>\n\n"
            f"Thread ID: <code>{thread_id}</code>\n"
            f"URL: {url}"
        )
    else:
        current_settings['dm_url'] = url
        save_settings()
        bot.send_message(message.chat.id, 
            "⚠️ <b>URL saved but thread ID not detected</b>\n\n"
            "Make sure the URL is correct:\n"
            "• https://www.instagram.com/direct/t/THREAD_ID/\n"
            "• Or provide thread ID directly"
        )

def send_start_message(message):
    """Wrapper for start command"""
    start_command(message)

# ========== MAIN ==========
if __name__ == "__main__":
    print(f"""
╔════════════════════════════════════════════╗
║     INSTAGRAM SPAM BOT v3.0              ║
║     FULLY FUNCTIONAL - ADMIN ACCESS      ║
╚════════════════════════════════════════════╝
    """)
    
    print(f"🔑 ADMIN USER ID: {ADMIN_USER_ID}")
    print(f"🤖 BOT USERNAME: {BOT_USERNAME}")
    print(f"📊 LOADED DATA:")
    print(f"   • Messages: {len(custom_messages)}")
    print(f"   • Sessions: {len(instagram_sessions)}")
    print(f"   • Users: {len(user_manager.get_all_users())}")
    
    try:
        bot_info = bot.get_me()
        print(f"\n✅ BOT STARTED SUCCESSFULLY!")
        print(f"✅ Bot: @{bot_info.username}")
        print(f"✅ Bot ID: {bot_info.id}")
        print(f"✅ Bot Name: {bot_info.first_name}")
    except Exception as e:
        print(f"\n❌ ERROR STARTING BOT: {e}")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print("📋 ADMIN COMMANDS AVAILABLE:")
    print(f"   • /admin - Admin panel")
    print(f"   • /users - View all users")
    print(f"   • /broadcast - Send message to all users")
    print(f"   • /addtime - Add time to user account")
    print(f"{'='*60}")
    print("🚀 Bot is now running...")
    print("Press Ctrl+C to stop")
    print(f"{'='*60}\n")
    
    # Start bot
    bot.infinity_polling()
