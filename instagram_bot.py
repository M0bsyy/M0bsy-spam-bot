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
ADMIN_USER_ID = "6107382622"

# Initialize bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# ========== INSTAGRAM API FUNCTIONS ==========
def generate_csrf_token(session_id):
    """Generate CSRF token from session ID"""
    chars = string.ascii_letters + string.digits
    random_part = ''.join(random.choice(chars) for _ in range(32))
    session_hash = hashlib.md5(session_id.encode()).hexdigest()[:16]
    return f"{session_hash}{random_part}"

def validate_instagram_session(session_id):
    """Check if Instagram session is valid"""
    try:
        csrf_token = generate_csrf_token(session_id)
        
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36',
        }
        
        response = requests.get(
            'https://www.instagram.com/accounts/edit/',
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200 and 'instagram' in response.text.lower():
            # Try to extract username
            username = "valid_account"
            if 'username' in response.text:
                import re
                match = re.search(r'"username":"([^"]+)"', response.text)
                if match:
                    username = match.group(1)
            return True, username, "Session valid"
        
        return False, None, f"Invalid session (HTTP {response.status_code})"
        
    except Exception as e:
        return False, None, f"Validation error: {str(e)}"

def send_instagram_message(session_id, thread_id, message):
    """Send actual Instagram message - SIMPLIFIED VERSION"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36',
            'x-ig-app-id': '936619743392459',
        }
        
        data = {
            'recipient_users': f'[["{thread_id}"]]',
            'client_context': str(int(time.time() * 1000)),
            'thread': thread_id,
            'text': message
        }
        
        response = requests.post(
            'https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/',
            headers=headers,
            data=data,
            timeout=10
        )
        
        if response.status_code == 200:
            return True, "✅ Sent"
        elif response.status_code == 400:
            # Try different endpoint
            return send_instagram_direct(session_id, thread_id, message)
        else:
            return False, f"❌ HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"❌ Error: {str(e)[:50]}"

def send_instagram_direct(session_id, thread_id, message):
    """Alternative direct message sending"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36',
        }
        
        # Try different API endpoint
        response = requests.post(
            f'https://www.instagram.com/api/v1/direct_v2/threads/{thread_id}/items/',
            headers=headers,
            data={'text': message},
            timeout=10
        )
        
        if response.status_code == 200:
            return True, "✅ Sent (Alt)"
        else:
            return False, f"❌ Alt {response.status_code}"
            
    except:
        return False, "❌ Failed"

def get_thread_id_from_url(url):
    """Extract thread ID from Instagram DM URL"""
    try:
        url = url.strip()
        # Remove query parameters
        url = url.split('?')[0]
        # Get the last part after /t/
        if '/direct/t/' in url:
            parts = url.split('/direct/t/')
            thread_id = parts[1].strip('/')
            return thread_id.split('/')[0]
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
    
    def add_user(self, user_id: str, username: str = ""):
        if str(user_id) not in self.users:
            self.users[str(user_id)] = {
                "username": username,
                "plan": "30_days_free",
                "expiry": (datetime.now() + timedelta(days=30)).isoformat(),
                "joined": datetime.now().isoformat(),
                "active": True,
                "is_admin": False
            }
            self.save_users()
            return True
        return False
    
    def is_admin(self, user_id: str) -> bool:
        user_data = self.users.get(str(user_id))
        return user_data.get("is_admin", False) if user_data else False
    
    def get_all_users(self):
        return self.users
    
    def set_admin(self, user_id: str, is_admin: bool = True):
        if str(user_id) in self.users:
            self.users[str(user_id)]["is_admin"] = is_admin
            self.save_users()
            return True
        return False

# ========== GLOBAL VARIABLES ==========
spam_active = False
spam_threads = []
success_count = 0
unsuccess_count = 0
counter_lock = threading.Lock()
custom_messages = []
instagram_sessions = []
current_settings = {
    "target": "",
    "delay_min": 0.5,  # 0.5 seconds minimum
    "delay_max": 1.5,  # 1.5 seconds maximum
    "message_count": 1000,
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
        custom_messages = []

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

# Load data on startup
load_messages()
load_sessions()

# ========== INITIALIZE ADMIN ==========
user_manager = UserManager()

def initialize_admin():
    """Ensure admin user exists"""
    admin_id = str(ADMIN_USER_ID)
    
    if admin_id not in user_manager.users:
        user_manager.users[admin_id] = {
            "username": "Admin",
            "plan": "lifetime",
            "expiry": (datetime.now() + timedelta(days=36500)).isoformat(),
            "joined": datetime.now().isoformat(),
            "active": True,
            "is_admin": True
        }
        user_manager.save_users()

initialize_admin()

# ========== HELPER FUNCTIONS ==========
def print_banner():
    return """
╔════════════════════════════════════════════╗
║        INSTAGRAM SPAM BOT v4.0             ║
║          ULTRA FAST MODE (1s)              ║
╚════════════════════════════════════════════╝
    """

def send_start_message(chat_id):
    """Send welcome message with instructions"""
    user_id = str(chat_id)
    is_admin = user_manager.is_admin(user_id)
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    welcome_text = f"""
{print_banner()}

📋 <b>Available Commands:</b>

🔹 /start - Show this help
🔹 /addmsg - Add spam message
🔹 /listmsg - List messages
🔹 /setup - Configure settings
🔹 /sessions - View sessions
🔹 /addsession - Add session
🔹 /start_spam - Start spam
🔹 /stop_spam - Stop spam
🔹 /stats - Show stats
🔹 /reset - Reset counters

{"🔹 /admin - Admin Panel" if is_admin else ""}

📊 <b>Current Status:</b>
• Messages: {len(custom_messages)}
• Valid Sessions: {valid_sessions}
• Target: {current_settings['target'] or 'Not set'}
• Group URL: {'✅ Set' if current_settings['dm_url'] else '❌ Not set'}
• Spam Status: {'🟢 ACTIVE' if spam_active else '🔴 INACTIVE'}
• Delay: {current_settings['delay_min']}-{current_settings['delay_max']}s
"""
    
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
        keyboard_buttons.append([InlineKeyboardButton(text="🔐 Admin Panel", callback_data="admin_panel")])
    
    keyboard = InlineKeyboardMarkup()
    for row in keyboard_buttons:
        keyboard.add(*row)
    
    bot.send_message(chat_id, welcome_text, reply_markup=keyboard)

# ========== MAIN COMMANDS ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start command"""
    user_id = str(message.from_user.id)
    username = message.from_user.username or message.from_user.first_name
    
    if user_id != ADMIN_USER_ID:
        user_manager.add_user(user_id, username)
    
    send_start_message(message.chat.id)

@bot.message_handler(commands=['admin'])
def admin_command(message):
    """Admin panel command"""
    user_id = str(message.from_user.id)
    
    if user_id != ADMIN_USER_ID and not user_manager.is_admin(user_id):
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    admin_text = """
🔐 <b>Admin Panel</b>

👥 <b>User Management:</b>
• /users - View all users

⚙️ <b>Bot Management:</b>
• /broadcast - Send message to all users
• /stats_all - Detailed statistics
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="👥 View Users", callback_data="admin_view_users"),
        InlineKeyboardButton(text="📊 Stats", callback_data="admin_stats")
    )
    keyboard.add(
        InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="🗑️ Cleanup", callback_data="admin_cleanup")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, admin_text, reply_markup=keyboard)

@bot.message_handler(commands=['users'])
def users_command(message):
    """View all users"""
    user_id = str(message.from_user.id)
    
    if user_id != ADMIN_USER_ID and not user_manager.is_admin(user_id):
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    users = user_manager.get_all_users()
    if not users:
        bot.send_message(message.chat.id, "📭 No users!")
        return
    
    response = "👥 <b>All Users:</b>\n\n"
    for uid, data in users.items():
        username = data.get('username', 'Unknown')
        is_admin = "✅" if data.get('is_admin') else "❌"
        
        response += f"ID: <code>{uid}</code>\n"
        response += f"   👤: {username}\n"
        response += f"   👑 Admin: {is_admin}\n\n"
    
    response += f"Total: {len(users)} users"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="◀️ Back", callback_data="admin_panel")
    )
    
    bot.send_message(message.chat.id, response, reply_markup=keyboard)

@bot.message_handler(commands=['addmsg'])
def addmsg_command(message):
    """Add a new message"""
    msg = bot.send_message(message.chat.id, "✍️ Send message to add (use {target} for target name):")
    bot.register_next_step_handler(msg, process_new_message)

def process_new_message(message):
    new_message = message.text
    custom_messages.append(new_message)
    save_messages()
    
    bot.send_message(message.chat.id, f"✅ Message added!\nTotal: {len(custom_messages)}")
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="➕ Add Another", callback_data="add_msg"),
        InlineKeyboardButton(text="📋 View All", callback_data="list_msg")
    )
    bot.send_message(message.chat.id, "Next:", reply_markup=keyboard)

@bot.message_handler(commands=['listmsg'])
def listmsg_command(message):
    """List all saved messages"""
    if not custom_messages:
        bot.send_message(message.chat.id, "📭 No messages!")
        return
    
    response = "📋 <b>Messages:</b>\n\n"
    for i, msg in enumerate(custom_messages, 1):
        preview = msg[:50] + "..." if len(msg) > 50 else msg
        response += f"{i}. <code>{preview}</code>\n"
    
    response += f"\nTotal: {len(custom_messages)}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="🗑️ Delete", callback_data="delete_msg_menu"),
        InlineKeyboardButton(text="◀️ Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, response, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "delete_msg_menu")
def delete_msg_menu_callback(call):
    """Show delete message menu"""
    if not custom_messages:
        bot.answer_callback_query(call.id, "No messages!")
        return
    
    keyboard = InlineKeyboardMarkup()
    for i in range(len(custom_messages)):
        preview = custom_messages[i][:30] + "..." if len(custom_messages[i]) > 30 else custom_messages[i]
        keyboard.add(InlineKeyboardButton(text=f"❌ Delete: {preview}", callback_data=f"delete_msg_{i}"))
    
    keyboard.add(InlineKeyboardButton(text="◀️ Back", callback_data="list_msg"))
    
    bot.edit_message_text(
        "🗑️ Select message to delete:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_msg_"))
def delete_msg_callback(call):
    """Delete message"""
    try:
        index = int(call.data.split("_")[2])
        if 0 <= index < len(custom_messages):
            deleted_msg = custom_messages.pop(index)
            save_messages()
            
            bot.answer_callback_query(call.id, "✅ Deleted!")
            listmsg_command(call.message)
    except:
        bot.answer_callback_query(call.id, "❌ Error!")

@bot.message_handler(commands=['addsession'])
def addsession_command(message):
    """Add new session"""
    msg = bot.send_message(message.chat.id, "🔑 Send Instagram session ID:\n\nGet from browser cookies:\n1. Login to Instagram\n2. F12 → Application → Cookies\n3. Copy 'sessionid'\n\nSend 'cancel' to cancel.")
    bot.register_next_step_handler(msg, process_new_session)

def process_new_session(message):
    if message.text.lower() == 'cancel':
        bot.send_message(message.chat.id, "❌ Cancelled.")
        return
    
    session_id = message.text.strip()
    
    bot.send_message(message.chat.id, "🔍 Validating...")
    valid, username, info = validate_instagram_session(session_id)
    
    if valid:
        session_data = {
            "session_id": session_id,
            "username": username,
            "status": "valid",
            "added": datetime.now().isoformat()
        }
        instagram_sessions.append(session_data)
        save_sessions()
        
        bot.send_message(message.chat.id, f"""
✅ Session added!

👤 @{username}
📅 {datetime.now().strftime('%H:%M:%S')}

Total valid: {len([s for s in instagram_sessions if s.get('status') == 'valid'])}
""")
    else:
        session_data = {
            "session_id": session_id,
            "username": "invalid",
            "status": "invalid",
            "error": info,
            "added": datetime.now().isoformat()
        }
        instagram_sessions.append(session_data)
        save_sessions()
        
        bot.send_message(message.chat.id, f"❌ Invalid session!\n\nError: {info}")

@bot.message_handler(commands=['sessions'])
def sessions_command(message):
    """View sessions"""
    if not instagram_sessions:
        bot.send_message(message.chat.id, "🔐 No sessions!")
        return
    
    valid_sessions = [s for s in instagram_sessions if s.get('status') == 'valid']
    
    response = "👥 <b>Sessions:</b>\n\n"
    
    if valid_sessions:
        response += "✅ <b>Valid:</b>\n"
        for i, session in enumerate(valid_sessions, 1):
            username = session.get('username', 'Unknown')
            response += f"{i}. @{username}\n"
    
    invalid_sessions = [s for s in instagram_sessions if s.get('status') != 'valid']
    if invalid_sessions:
        response += "\n❌ <b>Invalid:</b>\n"
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

@bot.callback_query_handler(func=lambda call: call.data == "delete_session_menu")
def delete_session_menu_callback(call):
    """Show delete session menu"""
    if not instagram_sessions:
        bot.answer_callback_query(call.id, "No sessions!")
        return
    
    keyboard = InlineKeyboardMarkup()
    for i in range(len(instagram_sessions)):
        username = instagram_sessions[i].get('username', 'Unknown')
        status = "✅" if instagram_sessions[i].get('status') == 'valid' else "❌"
        keyboard.add(InlineKeyboardButton(text=f"{status} Delete: {username}", callback_data=f"delete_session_{i}"))
    
    keyboard.add(InlineKeyboardButton(text="◀️ Back", callback_data="sessions"))
    
    bot.edit_message_text(
        "🗑️ Select session to delete:",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_session_"))
def delete_session_callback(call):
    """Delete session"""
    try:
        index = int(call.data.split("_")[2])
        if 0 <= index < len(instagram_sessions):
            instagram_sessions.pop(index)
            save_sessions()
            
            bot.answer_callback_query(call.id, "✅ Deleted!")
            sessions_command(call.message)
    except:
        bot.answer_callback_query(call.id, "❌ Error!")

@bot.message_handler(commands=['setup'])
def setup_command(message):
    """Configure settings"""
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
    
    current = f"""
⚙️ <b>Current Settings:</b>

🎯 Target: {current_settings['target'] or 'Not set'}
🔗 URL: {'✅' if current_settings['dm_url'] else '❌'}
⏱️ Delay: {current_settings['delay_min']}-{current_settings['delay_max']}s
📊 Count: {current_settings['message_count']}
"""
    
    bot.send_message(message.chat.id, current + "\nConfigure:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "set_target")
def set_target_callback(call):
    msg = bot.send_message(call.message.chat.id, "🎯 Send target username:")
    bot.register_next_step_handler(msg, process_target)

def process_target(message):
    current_settings['target'] = message.text
    bot.send_message(message.chat.id, f"✅ Target: {message.text}")

@bot.callback_query_handler(func=lambda call: call.data == "set_url")
def set_url_callback(call):
    msg = bot.send_message(call.message.chat.id, "🔗 Send Instagram DM URL:\n\nFormat: https://www.instagram.com/direct/t/THREAD_ID/")
    bot.register_next_step_handler(msg, process_url)

def process_url(message):
    url = message.text.strip()
    thread_id = get_thread_id_from_url(url)
    
    if thread_id:
        current_settings['dm_url'] = url
        bot.send_message(message.chat.id, f"✅ URL set!\nThread ID: {thread_id}")
    else:
        bot.send_message(message.chat.id, "❌ Invalid URL!")

@bot.callback_query_handler(func=lambda call: call.data == "set_count")
def set_count_callback(call):
    msg = bot.send_message(call.message.chat.id, "📊 Send message count:")
    bot.register_next_step_handler(msg, process_count)

def process_count(message):
    try:
        count = int(message.text)
        if 1 <= count <= 10000:
            current_settings['message_count'] = count
            bot.send_message(message.chat.id, f"✅ Count: {count}")
        else:
            bot.send_message(message.chat.id, "❌ 1-10000 only!")
    except:
        bot.send_message(message.chat.id, "❌ Numbers only!")

@bot.callback_query_handler(func=lambda call: call.data == "set_delay")
def set_delay_callback(call):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="⚡ 0.5-1.5s (ULTRA FAST)", callback_data="delay_0.5_1.5"),
        InlineKeyboardButton(text="🚀 1-3s (VERY FAST)", callback_data="delay_1_3")
    )
    keyboard.add(
        InlineKeyboardButton(text="💨 2-5s (FAST)", callback_data="delay_2_5"),
        InlineKeyboardButton(text="🐢 5-10s (SLOW)", callback_data="delay_5_10")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Back", callback_data="setup")
    )
    
    bot.send_message(call.message.chat.id, "⏱️ Select delay:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delay_"))
def process_delay_callback(call):
    data = call.data
    delays = data.split("_")[1:]
    current_settings['delay_min'] = float(delays[0])
    current_settings['delay_max'] = float(delays[1])
    
    bot.send_message(call.message.chat.id, f"✅ Delay: {delays[0]}-{delays[1]}s")

@bot.message_handler(commands=['start_spam'])
def start_spam_command(message):
    """Start spam"""
    # Check everything
    checks = []
    
    if not current_settings['target']:
        checks.append("❌ Set target first!")
    
    if not current_settings['dm_url']:
        checks.append("❌ Set URL first!")
    
    if not custom_messages:
        checks.append("❌ Add messages first!")
    
    valid_sessions = [s for s in instagram_sessions if s.get('status') == 'valid']
    if not valid_sessions:
        checks.append("❌ Add valid sessions first!")
    
    if checks:
        bot.send_message(message.chat.id, "\n".join(checks))
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
        args=(message.chat.id, thread_id)
    )
    thread.daemon = True
    thread.start()
    
    bot.send_message(message.chat.id, f"""
✅ <b>SPAM STARTED!</b>

🎯 Target: {current_settings['target']}
🔗 Thread: {thread_id}
📊 Messages: {len(custom_messages)}
👥 Accounts: {len(valid_sessions)}
⏱️ Delay: {current_settings['delay_min']}-{current_settings['delay_max']}s
📝 Count: {current_settings['message_count']}

⚡ <b>ULTRA FAST MODE ACTIVE!</b>
""")

def spam_worker(chat_id, thread_id):
    """Spam worker - ULTRA FAST"""
    global spam_active, success_count, unsuccess_count
    
    valid_sessions = [s for s in instagram_sessions if s.get('status') == 'valid']
    
    counter = 0
    session_index = 0
    
    bot.send_message(chat_id, f"⚡ Starting ULTRA FAST spam...")
    
    while spam_active and counter < current_settings['message_count']:
        try:
            # Get message
            msg = random.choice(custom_messages)
            formatted_msg = msg.replace("{target}", current_settings['target'])
            
            # Get session
            session = valid_sessions[session_index % len(valid_sessions)]
            session_id = session.get('session_id')
            username = session.get('username', 'acc')
            
            # Send message
            success, result = send_instagram_message(session_id, thread_id, formatted_msg)
            
            counter += 1
            
            if success:
                with counter_lock:
                    success_count += 1
                status = f"✅ {counter}: {result}"
            else:
                with counter_lock:
                    unsuccess_count += 1
                status = f"❌ {counter}: {result}"
            
            # Show progress every 50 messages
            if counter % 50 == 0:
                bot.send_message(
                    chat_id,
                    f"📊 {counter}/{current_settings['message_count']}\n"
                    f"✅ {success_count} | ❌ {unsuccess_count}\n"
                    f"📈 {success_count/(counter)*100:.1f}% success",
                    disable_notification=True
                )
            
            # Next session
            session_index += 1
            
            # ULTRA FAST DELAY
            delay = random.uniform(current_settings['delay_min'], current_settings['delay_max'])
            time.sleep(delay)
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)
    
    spam_active = False
    bot.send_message(chat_id, f"""
✅ SPAM COMPLETE!

📊 Final:
• Sent: {counter}
• ✅ Success: {success_count}
• ❌ Failed: {unsuccess_count}
• 📈 Rate: {success_count/(counter)*100:.1f}%

⚡ ULTRA FAST MODE FINISHED!
""")

@bot.message_handler(commands=['stop_spam'])
def stop_spam_command(message):
    """Stop spam"""
    global spam_active
    
    if not spam_active:
        bot.send_message(message.chat.id, "⚠️ Not running!")
        return
    
    spam_active = False
    bot.send_message(message.chat.id, "🛑 Stopping spam...")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Show stats"""
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    stats_text = f"""
📊 <b>STATISTICS</b>

✅ Success: {success_count}
❌ Failed: {unsuccess_count}
📈 Rate: {success_count/(success_count+unsuccess_count)*100:.1f}% if >0

💬 Messages: {len(custom_messages)}
👥 Sessions: {valid_sessions} valid

🎯 Target: {current_settings['target'] or 'None'}
🔗 URL: {'✅' if current_settings['dm_url'] else '❌'}

⏱️ Delay: {current_settings['delay_min']}-{current_settings['delay_max']}s
📝 Target: {current_settings['message_count']} msgs

🔴 Status: {'ACTIVE' if spam_active else 'INACTIVE'}
"""
    
    bot.send_message(message.chat.id, stats_text)

@bot.message_handler(commands=['reset'])
def reset_command(message):
    """Reset counters"""
    global success_count, unsuccess_count
    
    success_count = 0
    unsuccess_count = 0
    bot.send_message(message.chat.id, "🔄 Counters reset!")

# ========== CALLBACK HANDLERS ==========
@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def main_menu_callback(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    send_start_message(call.message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def admin_panel_callback(call):
    admin_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "admin_view_users")
def admin_view_users_callback(call):
    users_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "add_msg")
def add_msg_callback(call):
    msg = bot.send_message(call.message.chat.id, "✍️ Send message:")
    bot.register_next_step_handler(msg, process_new_message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "list_msg")
def list_msg_callback(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    listmsg_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "add_session")
def add_session_callback(call):
    msg = bot.send_message(call.message.chat.id, "🔑 Send session ID:")
    bot.register_next_step_handler(msg, process_new_session)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "list_sessions")
def list_sessions_callback(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    sessions_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "setup")
def setup_callback(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    setup_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "start_spam")
def start_spam_callback(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    start_spam_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "stop_spam")
def stop_spam_callback(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    stop_spam_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "stats")
def stats_callback(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    stats_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data in ["admin_stats", "admin_broadcast", "admin_cleanup"])
def admin_features_callback(call):
    bot.answer_callback_query(call.id, "Coming soon!")

# ========== MAIN ==========
if __name__ == "__main__":
    print(print_banner())
    print(f"🤖 Instagram Spam Bot v4.0 - ULTRA FAST MODE")
    print(f"👑 Admin: {ADMIN_USER_ID}")
    print(f"💬 Messages: {len(custom_messages)}")
    print(f"🔑 Sessions: {len(instagram_sessions)}")
    print(f"⚡ Delay: {current_settings['delay_min']}-{current_settings['delay_max']}s")
    
    try:
        bot_info = bot.get_me()
        print(f"✅ Bot: @{bot_info.username}")
        print("✅ Ready! Send /start")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        sys.exit(1)
    
    print("\n🚀 Starting...")
    bot.infinity_polling()
