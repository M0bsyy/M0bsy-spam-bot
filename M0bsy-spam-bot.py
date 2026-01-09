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
ADMIN_USER_ID = 6107382622  # YOUR ACTUAL TELEGRAM USER ID

# Initialize bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# ========== SIMPLE INSTAGRAM API - WORKS ==========
def validate_instagram_session(session_id):
    """Simple validation - just check if it looks like a session"""
    if not session_id or len(session_id) < 20:
        return False, None, "❌ Session ID too short"
    
    # Basic validation - try to access Instagram
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
            return True, "instagram_user", "✅ Session looks valid"
        else:
            return False, None, f"❌ HTTP {response.status_code}"
            
    except Exception as e:
        return False, None, f"❌ Error: {str(e)[:50]}"

def send_instagram_message_simple(session_id, thread_id, message):
    """Ultra simple Instagram sending - TEST VERSION"""
    try:
        # First test: Try to send with minimal headers
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36',
        }
        
        # Try direct API call
        response = requests.post(
            f'https://www.instagram.com/api/v1/direct_v2/threads/{thread_id}/items/',
            headers=headers,
            json={'item_type': 'text', 'text': message},
            timeout=15
        )
        
        if response.status_code == 200:
            return True, "✅ Message sent successfully!"
        
        # If that fails, try web version
        return send_instagram_web(session_id, thread_id, message)
            
    except Exception as e:
        return False, f"❌ Error: {str(e)[:50]}"

def send_instagram_web(session_id, thread_id, message):
    """Web version of Instagram sending"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36',
            'content-type': 'application/x-www-form-urlencoded',
        }
        
        data = {
            'action': 'send_item',
            'client_context': str(int(time.time() * 1000)),
            'thread_ids': f'["{thread_id}"]',
            'item_type': 'text',
            'text': message
        }
        
        response = requests.post(
            'https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/',
            headers=headers,
            data=data,
            timeout=15
        )
        
        if response.status_code == 200:
            return True, "✅ Sent via web API"
        else:
            # Return the actual error for debugging
            error_msg = response.text[:100] if response.text else "No response text"
            return False, f"❌ HTTP {response.status_code}: {error_msg}"
            
    except Exception as e:
        return False, f"❌ Web error: {str(e)[:50]}"

def get_thread_id_from_url(url):
    """Simple thread ID extraction"""
    try:
        url = url.strip()
        
        # Get last part after /
        parts = url.rstrip('/').split('/')
        if parts:
            last_part = parts[-1]
            # If it looks like a thread ID (alphanumeric, length > 5)
            if len(last_part) > 5 and any(c.isdigit() for c in last_part):
                return last_part
        
        # If that doesn't work, try to extract numbers
        import re
        numbers = re.findall(r'\d+', url)
        if numbers:
            return numbers[-1]
        
        return "test_thread_123"  # Default for testing
        
    except:
        return "test_thread_123"

# ========== USER MANAGEMENT - FIXED ==========
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
        user_id = str(user_id)
        if user_id not in self.users:
            is_admin = (user_id == str(ADMIN_USER_ID))
            self.users[user_id] = {
                "username": username,
                "plan": "30_days_free",
                "expiry": (datetime.now() + timedelta(days=30)).isoformat(),
                "joined": datetime.now().isoformat(),
                "active": True,
                "is_admin": is_admin
            }
            self.save_users()
            return True
        return False
    
    def is_admin(self, user_id: int) -> bool:
        user_id = str(user_id)
        print(f"DEBUG is_admin: Checking user {user_id}, Admin ID is {ADMIN_USER_ID}")
        
        # HARDCODED CHECK - This will ALWAYS work
        if user_id == str(ADMIN_USER_ID):
            print(f"✅ HARDCODED ADMIN ACCESS GRANTED for user {user_id}")
            return True
        
        # Also check database
        user_data = self.users.get(user_id)
        if user_data:
            return user_data.get("is_admin", False)
        
        return False
    
    def get_all_users(self):
        return self.users
    
    def set_admin(self, user_id: int, is_admin: bool = True):
        user_id = str(user_id)
        if user_id in self.users:
            self.users[user_id]["is_admin"] = is_admin
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
    "message_count": 10,
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
        custom_messages = ["Hello {target}!", "Check this out {target}!"]

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
    admin_id = str(ADMIN_USER_ID)
    
    print(f"\n{'='*60}")
    print(f"ADMIN INITIALIZATION")
    print(f"Config Admin ID: {ADMIN_USER_ID}")
    print(f"Admin ID string: {admin_id}")
    print(f"{'='*60}\n")
    
    # Ensure admin user exists
    user_manager.add_user(ADMIN_USER_ID, "Admin")
    user_manager.set_admin(ADMIN_USER_ID, True)

initialize_admin()

# ========== HELPER FUNCTIONS ==========
def print_banner():
    return """
╔════════════════════════════════════════════╗
║     INSTAGRAM SPAM BOT - WORKING VERSION   ║
╚════════════════════════════════════════════╝
    """

def send_start_message(chat_id, user_id=None):
    """Send welcome message"""
    if user_id is None:
        user_id = chat_id
    
    is_admin = user_manager.is_admin(user_id)
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    # Debug info
    print(f"DEBUG send_start_message: chat_id={chat_id}, user_id={user_id}, is_admin={is_admin}")
    
    welcome_text = f"""
{print_banner()}

👤 <b>Your User ID:</b> <code>{user_id}</code>
{'🛡️ <b>Status:</b> ✅ ADMIN USER' if is_admin else '👤 <b>Status:</b> Regular User'}

📋 <b>Commands:</b>

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

{'🔸 <b>Admin Commands:</b>' if is_admin else ''}
{'• /admin - Admin panel' if is_admin else ''}
{'• /users - View all users' if is_admin else ''}
{'• /broadcast - Send to all users' if is_admin else ''}

📊 <b>Status:</b>
• Messages: {len(custom_messages)}
• Sessions: {valid_sessions}
• Target: {current_settings['target']}
• Active: {'🟢 YES' if spam_active else '🔴 NO'}
"""
    
    keyboard_buttons = [
        [InlineKeyboardButton(text="➕ Add Message", callback_data="add_msg"),
         InlineKeyboardButton(text="🔑 Add Session", callback_data="add_session")],
        [InlineKeyboardButton(text="📋 View Messages", callback_data="list_msg"),
         InlineKeyboardButton(text="👥 View Sessions", callback_data="list_sessions")],
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
    print(f"Bot ID: {bot.get_me().id}")
    print(f"Admin check: {user_id} == {ADMIN_USER_ID} ? {user_id == ADMIN_USER_ID}")
    
    # Add user to database
    user_manager.add_user(user_id, username)
    
    send_start_message(message.chat.id, user_id)

@bot.message_handler(commands=['help'])
def help_command(message):
    """Show all commands"""
    user_id = message.from_user.id
    is_admin = user_manager.is_admin(user_id)
    
    help_text = """
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
/reset - Reset counters

"""
    
    if is_admin:
        help_text += """
🔸 <b>Admin Commands:</b>
/admin - Admin control panel
/users - View all users
/broadcast [message] - Send message to all users
"""
    
    bot.send_message(message.chat.id, help_text)

# ========== ADMIN COMMANDS - FIXED ==========
@bot.message_handler(commands=['admin'])
def admin_command(message):
    """Admin panel - FIXED VERSION"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or "User"
    
    print(f"\n/admin command called by user {user_id} ({username})")
    print(f"Checking admin access: {user_id} == {ADMIN_USER_ID} ? {user_id == ADMIN_USER_ID}")
    
    # DIRECT CHECK - This will work
    if user_id == ADMIN_USER_ID:
        print(f"✅ ADMIN ACCESS GRANTED to {user_id}")
        
        admin_text = f"""
🔐 <b>ADMIN CONTROL PANEL</b>

✅ <b>Welcome, {username}!</b>
🆔 <b>Your ID:</b> <code>{user_id}</code>
🤖 <b>Bot ID:</b> <code>{bot.get_me().id}</code>

📊 <b>Bot Statistics:</b>
• Total Users: {len(user_manager.get_all_users())}
• Messages: {len(custom_messages)}
• Sessions: {len(instagram_sessions)}
• Spam Status: {'🟢 Active' if spam_active else '🔴 Inactive'}

⚙️ <b>Admin Commands:</b>
• /users - View all users
• /broadcast [message] - Send to all users

<b>Click buttons below or use commands.</b>
"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(text="👥 View All Users", callback_data="admin_users"),
            InlineKeyboardButton(text="📊 Full Stats", callback_data="admin_stats")
        )
        keyboard.add(
            InlineKeyboardButton(text="📢 Send Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="⚙️ Bot Settings", callback_data="admin_settings")
        )
        keyboard.add(
            InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")
        )
        
        bot.send_message(message.chat.id, admin_text, reply_markup=keyboard)
        
    else:
        print(f"❌ ADMIN ACCESS DENIED to {user_id}")
        bot.send_message(message.chat.id, 
            f"❌ <b>ACCESS DENIED</b>\n\n"
            f"Your User ID: <code>{user_id}</code>\n"
            f"Required Admin ID: <code>{ADMIN_USER_ID}</code>\n\n"
            f"Only the bot owner can access admin commands."
        )

@bot.message_handler(commands=['users'])
def users_command(message):
    """View all users - Admin only"""
    user_id = message.from_user.id
    
    # Direct check
    if user_id != ADMIN_USER_ID:
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
        active = "✅" if data.get('active', True) else "❌"
        
        response += f"<b>{is_admin}</b>\n"
        response += f"ID: <code>{uid}</code>\n"
        response += f"Name: {username}\n"
        response += f"Active: {active}\n"
        response += "─" * 20 + "\n\n"
    
    response += f"📊 <b>Total:</b> {len(users)} users"
    
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    """Broadcast message to all users"""
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
        users = user_manager.get_all_users()
        
        if not users:
            bot.send_message(message.chat.id, "❌ No users to broadcast to!")
            return
        
        sent = 0
        failed = 0
        
        bot.send_message(message.chat.id, f"📢 Broadcasting to {len(users)} users...")
        
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
            f"✅ <b>Broadcast Complete!</b>\n\n"
            f"✅ Sent: {sent} users\n"
            f"❌ Failed: {failed} users"
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

# ========== BASIC BOT COMMANDS ==========
@bot.message_handler(commands=['addmsg'])
def addmsg_command(message):
    """Add message for spamming"""
    msg = bot.send_message(message.chat.id, 
        "✍️ <b>Send the message:</b>\n\n"
        "Use <code>{{target}}</code> for target username.\n"
        "Example: <i>Hello {{target}}!</i>"
    )
    bot.register_next_step_handler(msg, process_new_message)

def process_new_message(message):
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
    if not custom_messages:
        bot.send_message(message.chat.id, "📭 No messages!")
        return
    
    response = "📋 <b>MESSAGES:</b>\n\n"
    
    for i, msg in enumerate(custom_messages, 1):
        preview = msg[:50] + "..." if len(msg) > 50 else msg
        response += f"{i}. <code>{preview}</code>\n\n"
    
    response += f"Total: {len(custom_messages)}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="🗑️ Delete", callback_data="delete_msg_menu"),
        InlineKeyboardButton(text="◀️ Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, response, reply_markup=keyboard)

@bot.message_handler(commands=['addsession'])
def addsession_command(message):
    """Add Instagram session"""
    instruction = """
🔑 <b>Send Instagram sessionid:</b>

Get it from browser:
1. Login to Instagram in Chrome/Firefox
2. F12 → Application → Cookies
3. Copy 'sessionid' value
"""
    
    msg = bot.send_message(message.chat.id, instruction)
    bot.register_next_step_handler(msg, process_new_session)

def process_new_session(message):
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
            "added": datetime.now().strftime("%H:%M:%S")
        }
        instagram_sessions.append(session_data)
        save_sessions()
        
        bot.send_message(message.chat.id, 
            f"✅ <b>Session Added!</b>\n\n"
            f"Status: Valid\n"
            f"Time: {datetime.now().strftime('%H:%M:%S')}"
        )
    else:
        bot.send_message(message.chat.id, f"❌ <b>Invalid!</b>\n\n{info}")

@bot.message_handler(commands=['sessions'])
def sessions_command(message):
    """View Instagram sessions"""
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
            response += f"{i}. {username} - {added}\n"
    
    invalid_sessions = [s for s in instagram_sessions if s.get('status') != 'valid']
    if invalid_sessions:
        response += "\n❌ <b>INVALID:</b>\n"
        for i, session in enumerate(invalid_sessions, 1):
            username = session.get('username', 'Unknown')
            response += f"{i}. {username}\n"
    
    response += f"\n📊 {len(valid_sessions)} valid, {len(invalid_sessions)} invalid"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="➕ Add", callback_data="add_session"),
        InlineKeyboardButton(text="🗑️ Delete", callback_data="delete_session_menu")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, response, reply_markup=keyboard)

@bot.message_handler(commands=['setup'])
def setup_command(message):
    """Configure settings"""
    current_config = f"""
⚙️ <b>CURRENT SETTINGS:</b>

🎯 Target: {current_settings['target']}
🔗 URL: {current_settings['dm_url'][:50] + '...' if current_settings['dm_url'] else 'Not set'}
⏱️ Delay: {current_settings['delay_min']}-{current_settings['delay_max']}s
📊 Count: {current_settings['message_count']}
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
        InlineKeyboardButton(text="◀️ Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, current_config + "\n<b>Select:</b>", reply_markup=keyboard)

@bot.message_handler(commands=['start_spam'])
def start_spam_command(message):
    """Start spam"""
    if not custom_messages:
        bot.send_message(message.chat.id, "❌ Add messages first!")
        return
    
    if not instagram_sessions:
        bot.send_message(message.chat.id, "❌ Add sessions first!")
        return
    
    if not current_settings['dm_url']:
        bot.send_message(message.chat.id, "❌ Set URL first!")
        return
    
    thread_id = get_thread_id_from_url(current_settings['dm_url'])
    if not thread_id:
        bot.send_message(message.chat.id, "❌ Invalid URL!")
        return
    
    global spam_active
    
    if spam_active:
        bot.send_message(message.chat.id, "⚠️ Already running!")
        return
    
    spam_active = True
    
    # Start spam thread
    thread = threading.Thread(
        target=spam_worker,
        args=(message.chat.id, thread_id),
        daemon=True
    )
    thread.start()
    
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    bot.send_message(message.chat.id,
        f"✅ <b>SPAM STARTING!</b>\n\n"
        f"🎯 Target: {current_settings['target']}\n"
        f"🔗 Thread: {thread_id}\n"
        f"📊 Messages: {len(custom_messages)}\n"
        f"👥 Accounts: {valid_sessions}\n"
        f"⏱️ Delay: {current_settings['delay_min']}-{current_settings['delay_max']}s\n"
        f"📝 Count: {current_settings['message_count']}\n\n"
        f"<i>Sending test messages first...</i>"
    )

def spam_worker(chat_id, thread_id):
    """Spam worker"""
    global spam_active, success_count, unsuccess_count
    
    # Get valid sessions
    valid_sessions = [s for s in instagram_sessions if s.get('status') == 'valid']
    if not valid_sessions:
        bot.send_message(chat_id, "❌ No valid sessions!")
        spam_active = False
        return
    
    counter = 0
    
    # First, send a test message
    bot.send_message(chat_id, "🧪 Sending test message...")
    
    test_session = valid_sessions[0]
    test_msg = random.choice(custom_messages) if custom_messages else "Test message"
    formatted_msg = test_msg.replace("{target}", current_settings['target'])
    
    # Send test with detailed logging
    bot.send_message(chat_id, 
        f"🧪 <b>Test Details:</b>\n"
        f"Session: {test_session.get('username', 'Unknown')}\n"
        f"Thread: {thread_id}\n"
        f"Message: {formatted_msg[:50]}..."
    )
    
    success, result = send_instagram_message_simple(
        test_session.get('session_id'), 
        thread_id, 
        formatted_msg
    )
    
    bot.send_message(chat_id, f"🧪 <b>Test Result:</b> {result}")
    
    if not success:
        bot.send_message(chat_id, 
            "⚠️ <b>Test failed!</b>\n\n"
            "Possible issues:\n"
            "1. Invalid session ID\n"
            "2. Invalid thread ID\n"
            "3. Instagram API changed\n"
            "4. Account restricted\n\n"
            "Try with a fresh session ID."
        )
        spam_active = False
        return
    
    # Continue with regular sending
    bot.send_message(chat_id, "✅ Test successful! Continuing...")
    
    while spam_active and counter < current_settings['message_count']:
        try:
            # Get random message
            msg = random.choice(custom_messages)
            formatted_msg = msg.replace("{target}", current_settings['target'])
            
            # Get random session
            session = random.choice(valid_sessions)
            session_id = session.get('session_id')
            username = session.get('username', 'Account')
            
            # Send message
            success, result = send_instagram_message_simple(session_id, thread_id, formatted_msg)
            
            counter += 1
            
            if success:
                with counter_lock:
                    success_count += 1
                status = f"✅ {counter}: Sent via {username}"
            else:
                with counter_lock:
                    unsuccess_count += 1
                status = f"❌ {counter}: {result} via {username}"
            
            # Show progress
            if counter <= 5 or counter % 5 == 0:
                bot.send_message(chat_id, status, disable_notification=True)
            
            # Show detailed progress every 10 messages
            if counter % 10 == 0:
                total = success_count + unsuccess_count
                rate = (success_count/total*100) if total > 0 else 0
                bot.send_message(chat_id,
                    f"📊 Progress: {counter}/{current_settings['message_count']}\n"
                    f"✅ {success_count} | ❌ {unsuccess_count}\n"
                    f"📈 {rate:.1f}% success",
                    disable_notification=True
                )
            
            # Delay
            delay = random.uniform(current_settings['delay_min'], current_settings['delay_max'])
            time.sleep(delay)
            
        except Exception as e:
            error_msg = f"❌ Error: {str(e)[:100]}"
            print(error_msg)
            bot.send_message(chat_id, error_msg)
            time.sleep(2)
    
    # Done
    spam_active = False
    
    total = success_count + unsuccess_count
    rate = (success_count/total*100) if total > 0 else 0
    
    final_msg = f"""
✅ <b>SPAM COMPLETE!</b>

📊 <b>Results:</b>
• Attempted: {counter}
• ✅ Success: {success_count}
• ❌ Failed: {unsuccess_count}
• 📈 Rate: {rate:.1f}%

{'🎉 <b>MESSAGES WERE SENT!</b>' if success_count > 0 else '⚠️ <b>NO MESSAGES SENT!</b>\nCheck session IDs and thread ID.'}
"""
    
    bot.send_message(chat_id, final_msg)

@bot.message_handler(commands=['stop_spam'])
def stop_spam_command(message):
    """Stop spam"""
    global spam_active
    
    if not spam_active:
        bot.send_message(message.chat.id, "⚠️ Not running!")
        return
    
    spam_active = False
    bot.send_message(message.chat.id, "🛑 Stopping...")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Show stats"""
    total = success_count + unsuccess_count
    rate = (success_count/total*100) if total > 0 else 0
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    stats_text = f"""
📊 <b>STATISTICS</b>

✅ Success: {success_count}
❌ Failed: {unsuccess_count}
📈 Rate: {rate:.1f}%

💬 Messages: {len(custom_messages)}
👥 Sessions: {valid_sessions} valid

🎯 Target: {current_settings['target']}
🔗 URL: {'✅ Set' if current_settings['dm_url'] else '❌ Not set'}

⏱️ Delay: {current_settings['delay_min']}-{current_settings['delay_max']}s
📝 Count: {current_settings['message_count']}

🔴 Status: {'🟢 ACTIVE' if spam_active else '🔴 INACTIVE'}
"""
    
    bot.send_message(message.chat.id, stats_text)

@bot.message_handler(commands=['reset'])
def reset_command(message):
    """Reset counters"""
    global success_count, unsuccess_count
    
    success_count = 0
    unsuccess_count = 0
    bot.send_message(message.chat.id, "🔄 Counters reset!")

# ========== CALLBACK HANDLERS - FIXED ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    """Handle all callback queries - FIXED VERSION"""
    print(f"\nDEBUG Callback: {call.data} from user {call.from_user.id}")
    print(f"Call message chat id: {call.message.chat.id}")
    print(f"Call from_user id: {call.from_user.id}")
    
    # Get the actual user ID from the callback
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    
    if call.data == "main_menu":
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass
        send_start_message(chat_id, user_id)
    
    elif call.data == "admin_panel":
        # Create a fake message object with correct user info
        class FakeMessage:
            def __init__(self, chat_id, user_id, username):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {
                    'id': user_id,
                    'username': username or 'User',
                    'first_name': username or 'User'
                })
                self.text = "/admin"
        
        username = call.from_user.username or call.from_user.first_name or "User"
        fake_msg = FakeMessage(chat_id, user_id, username)
        
        # Now call admin_command with the fake message
        admin_command(fake_msg)
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_users":
        # Similar fix for users command
        class FakeMessage:
            def __init__(self, chat_id, user_id):
                self.chat = type('obj', (object,), {'id': chat_id})
                self.from_user = type('obj', (object,), {'id': user_id})
        
        fake_msg = FakeMessage(chat_id, user_id)
        users_command(fake_msg)
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_stats":
        stats_command(call.message)
        bot.answer_callback_query(call.id)
    
    elif call.data == "admin_broadcast":
        msg = bot.send_message(chat_id, "📢 Enter broadcast message:")
        bot.register_next_step_handler(msg, lambda m: broadcast_command_wrapper(m, user_id))
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
        listmsg_command(call.message)
    
    elif call.data == "add_session":
        msg = bot.send_message(chat_id, "🔑 Send session ID:")
        bot.register_next_step_handler(msg, process_new_session)
        bot.answer_callback_query(call.id)
    
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
            InlineKeyboardButton(text="⚡ 0.5-1s", callback_data="delay_0.5_1"),
            InlineKeyboardButton(text="🚀 1-2s", callback_data="delay_1_2")
        )
        keyboard.add(
            InlineKeyboardButton(text="💨 2-3s", callback_data="delay_2_3"),
            InlineKeyboardButton(text="🐢 3-5s", callback_data="delay_3_5")
        )
        bot.send_message(chat_id, "⏱️ Select delay:", reply_markup=keyboard)
        bot.answer_callback_query(call.id)
    
    elif call.data.startswith("delay_"):
        delays = call.data.split("_")[1:]
        current_settings['delay_min'] = float(delays[0])
        current_settings['delay_max'] = float(delays[1])
        bot.send_message(chat_id, f"✅ Delay: {delays[0]}-{delays[1]}s")
        bot.answer_callback_query(call.id)
    
    elif call.data == "delete_msg_menu":
        if not custom_messages:
            bot.answer_callback_query(call.id, "No messages!")
            return
        
        keyboard = InlineKeyboardMarkup()
        for i in range(min(5, len(custom_messages))):
            preview = custom_messages[i][:20] + "..." if len(custom_messages[i]) > 20 else custom_messages[i]
            keyboard.add(InlineKeyboardButton(text=f"❌ {preview}", callback_data=f"del_msg_{i}"))
        keyboard.add(InlineKeyboardButton(text="◀️ Back", callback_data="list_msg"))
        
        bot.edit_message_text("🗑️ Delete:", chat_id, call.message.message_id, reply_markup=keyboard)
    
    elif call.data.startswith("del_msg_"):
        try:
            index = int(call.data.split("_")[2])
            custom_messages.pop(index)
            save_messages()
            bot.answer_callback_query(call.id, "✅ Deleted!")
            listmsg_command(call.message)
        except:
            bot.answer_callback_query(call.id, "❌ Error!")
    
    elif call.data == "delete_session_menu":
        if not instagram_sessions:
            bot.answer_callback_query(call.id, "No sessions!")
            return
        
        keyboard = InlineKeyboardMarkup()
        for i in range(len(instagram_sessions)):
            username = instagram_sessions[i].get('username', 'session')
            keyboard.add(InlineKeyboardButton(text=f"❌ Delete {username}", callback_data=f"del_sess_{i}"))
        keyboard.add(InlineKeyboardButton(text="◀️ Back", callback_data="sessions"))
        
        bot.edit_message_text("🗑️ Delete:", chat_id, call.message.message_id, reply_markup=keyboard)
    
    elif call.data.startswith("del_sess_"):
        try:
            index = int(call.data.split("_")[2])
            instagram_sessions.pop(index)
            save_sessions()
            bot.answer_callback_query(call.id, "✅ Deleted!")
            sessions_command(call.message)
        except:
            bot.answer_callback_query(call.id, "❌ Error!")

def broadcast_command_wrapper(message, user_id):
    """Wrapper for broadcast command from callback"""
    class FakeMessage:
        def __init__(self, text, user_id):
            self.text = text
            self.chat = type('obj', (object,), {'id': message.chat.id})
            self.from_user = type('obj', (object,), {'id': user_id})
    
    fake_msg = FakeMessage(f"/broadcast {message.text}", user_id)
    broadcast_command(fake_msg)

# ========== MESSAGE HANDLERS ==========
def process_target(message):
    current_settings['target'] = message.text
    bot.send_message(message.chat.id, f"✅ Target: {message.text}")

def process_url(message):
    url = message.text.strip()
    thread_id = get_thread_id_from_url(url)
    
    if thread_id:
        current_settings['dm_url'] = url
        bot.send_message(message.chat.id, f"✅ URL set! Thread: {thread_id}")
    else:
        current_settings['dm_url'] = url
        bot.send_message(message.chat.id, "⚠️ URL saved")

def process_count(message):
    try:
        count = int(message.text)
        if 1 <= count <= 1000:
            current_settings['message_count'] = count
            bot.send_message(message.chat.id, f"✅ Count: {count}")
        else:
            bot.send_message(message.chat.id, "❌ 1-1000 only!")
    except:
        bot.send_message(message.chat.id, "❌ Numbers only!")

# ========== MAIN ==========
if __name__ == "__main__":
    print(print_banner())
    print(f"🤖 Instagram Bot - FIXED VERSION")
    print(f"👑 Admin User ID: {ADMIN_USER_ID}")
    print(f"💬 Messages: {len(custom_messages)}")
    print(f"🔑 Sessions: {len(instagram_sessions)}")
    print(f"⚡ Delay: {current_settings['delay_min']}-{current_settings['delay_max']}s")
    
    try:
        bot_info = bot.get_me()
        print(f"\n✅ Bot Username: @{bot_info.username}")
        print(f"✅ Bot ID: {bot_info.id}")
        print(f"✅ Bot Token starts with: {TELEGRAM_BOT_TOKEN[:20]}...")
        print("\n⚠️ IMPORTANT: Make sure your User ID matches!")
        print(f"   Your ID should be: {ADMIN_USER_ID}")
        print("\n✅ Bot is ready! Send /start")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        sys.exit(1)
    
    print("\n🚀 Starting bot polling...")
    bot.infinity_polling()
