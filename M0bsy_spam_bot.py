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
def generate_csrf_token():
    """Generate random CSRF token"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(32))

def validate_instagram_session(session_id):
    """Check if Instagram session is valid - SIMPLIFIED"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36',
        }
        
        # Try to access Instagram homepage with session
        response = requests.get(
            'https://www.instagram.com/api/v1/users/web_profile_info/?username=instagram',
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return True, "instagram_user", "Session valid"
        else:
            # Try alternative check
            response2 = requests.get(
                'https://www.instagram.com/accounts/edit/',
                headers=headers,
                timeout=30
            )
            if response2.status_code == 200:
                return True, "valid_user", "Session valid"
        
        return False, None, f"Invalid (HTTP {response.status_code})"
        
    except Exception as e:
        return False, None, f"Error: {str(e)}"

def send_instagram_message_simple(session_id, thread_id, message):
    """Simplified Instagram message sending"""
    try:
        # Generate random headers
        csrf_token = generate_csrf_token()
        
        headers = {
            'cookie': f'sessionid={session_id}; csrftoken={csrf_token}',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36',
            'x-csrftoken': csrf_token,
            'x-ig-app-id': '936619743392459',
            'x-requested-with': 'XMLHttpRequest',
            'origin': 'https://www.instagram.com',
            'referer': f'https://www.instagram.com/direct/t/{thread_id}/',
        }
        
        # Prepare data
        data = {
            'action': 'send_item',
            'client_context': str(int(time.time() * 1000)),
            'thread_ids': f'["{thread_id}"]',
            'item_type': 'text',
            'text': message
        }
        
        # Send request
        response = requests.post(
            'https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/',
            headers=headers,
            data=data,
            timeout=10
        )
        
        # Check response
        if response.status_code == 200:
            return True, "✅ Sent"
        else:
            # Try alternative endpoint
            return send_instagram_alternative(session_id, thread_id, message)
            
    except Exception as e:
        return False, f"❌ {str(e)[:50]}"

def send_instagram_alternative(session_id, thread_id, message):
    """Alternative Instagram sending method"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36',
            'x-ig-app-id': '936619743392459',
        }
        
        # Alternative API endpoint
        response = requests.post(
            f'https://www.instagram.com/api/v1/direct_v2/threads/{thread_id}/items/',
            headers=headers,
            json={'item_type': 'text', 'text': message},
            timeout=10
        )
        
        if response.status_code == 200:
            return True, "✅ Sent (Alt)"
        else:
            return False, f"❌ HTTP {response.status_code}"
            
    except:
        return False, "❌ Failed"

def get_thread_id_from_url(url):
    """Extract thread ID from Instagram DM URL"""
    try:
        url = url.strip()
        # Look for thread ID pattern
        import re
        patterns = [
            r'direct/t/([^/?]+)',
            r't/([^/?]+)',
            r'thread_([^_]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                thread_id = match.group(1)
                if len(thread_id) > 5:  # Valid thread ID
                    return thread_id
        
        # Try to extract numbers from URL
        numbers = re.findall(r'\d+', url)
        if numbers:
            return numbers[-1]  # Use last number group
            
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
        if user_data:
            return user_data.get("is_admin", False)
        return False
    
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
    "delay_min": 0.5,
    "delay_max": 1.5,
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
    """Force create admin user on startup"""
    admin_id = str(ADMIN_USER_ID)
    
    # Always set as admin, even if user exists
    user_manager.users[admin_id] = {
        "username": "Admin",
        "plan": "lifetime",
        "expiry": (datetime.now() + timedelta(days=36500)).isoformat(),
        "joined": datetime.now().isoformat(),
        "active": True,
        "is_admin": True  # THIS IS IMPORTANT
    }
    
    user_manager.save_users()
    print(f"✅ Admin user {admin_id} initialized")

initialize_admin()

# ========== HELPER FUNCTIONS ==========
def print_banner():
    return """
╔════════════════════════════════════════════╗
║        INSTAGRAM SPAM BOT v5.0             ║
║          WORKING VERSION                    ║
╚════════════════════════════════════════════╝
    """

def send_start_message(chat_id):
    """Send welcome message"""
    user_id = str(chat_id)
    is_admin = user_manager.is_admin(user_id)
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    welcome_text = f"""
{print_banner()}

📋 <b>Commands:</b>

🔹 /start - Show this
🔹 /addmsg - Add message
🔹 /listmsg - List messages  
🔹 /setup - Settings
🔹 /sessions - Sessions
🔹 /addsession - Add session
🔹 /start_spam - Start spam
🔹 /stop_spam - Stop spam
🔹 /stats - Stats
🔹 /reset - Reset

{"🔹 /admin - Admin Panel" if is_admin else ""}

📊 <b>Status:</b>
• Messages: {len(custom_messages)}
• Sessions: {valid_sessions}
• Target: {current_settings['target'] or 'Not set'}
• URL: {'✅' if current_settings['dm_url'] else '❌'}
• Active: {'🟢' if spam_active else '🔴'}
"""
    
    keyboard_buttons = [
        [InlineKeyboardButton(text="➕ Add Message", callback_data="add_msg"),
         InlineKeyboardButton(text="🔑 Add Session", callback_data="add_session")],
        [InlineKeyboardButton(text="📋 Messages", callback_data="list_msg"),
         InlineKeyboardButton(text="👥 Sessions", callback_data="list_sessions")],
        [InlineKeyboardButton(text="⚙️ Setup", callback_data="setup"),
         InlineKeyboardButton(text="▶️ Start", callback_data="start_spam")],
        [InlineKeyboardButton(text="⏹️ Stop", callback_data="stop_spam"),
         InlineKeyboardButton(text="📊 Stats", callback_data="stats")]
    ]
    
    if is_admin:
        keyboard_buttons.append([InlineKeyboardButton(text="🔐 Admin", callback_data="admin_panel")])
    
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
    
    user_manager.add_user(user_id, username)
    
    # Special check for admin
    if user_id == ADMIN_USER_ID:
        user_manager.set_admin(user_id, True)
    
    send_start_message(message.chat.id)

@bot.message_handler(commands=['admin'])
def admin_command(message):
    """Admin panel - FIXED VERSION"""
    user_id = str(message.from_user.id)
    
    # DEBUG: Check user ID
    print(f"DEBUG: User {user_id} trying to access admin")
    print(f"DEBUG: Admin ID is {ADMIN_USER_ID}")
    print(f"DEBUG: User == Admin? {user_id == ADMIN_USER_ID}")
    
    # DIRECT HARDCODED CHECK - If user ID matches admin ID, grant access
    if user_id == ADMIN_USER_ID:
        # Force set as admin
        user_manager.set_admin(user_id, True)
        print(f"DEBUG: Hardcoded admin access granted to {user_id}")
    elif not user_manager.is_admin(user_id):
        print(f"DEBUG: User {user_id} is NOT admin in database")
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    print(f"DEBUG: Admin access granted to {user_id}")
    
    admin_text = """
🔐 <b>ADMIN PANEL</b>

👤 <b>Your Admin Status:</b>
• User ID: <code>{user_id}</code>
• Admin Access: ✅ GRANTED

📋 <b>Admin Commands:</b>
• /users - View all users
• /stats_all - Full statistics
• /broadcast - Send message to all users
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="👥 View Users", callback_data="admin_view_users"),
        InlineKeyboardButton(text="📊 Full Stats", callback_data="admin_stats")
    )
    keyboard.add(
        InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="⚙️ Settings", callback_data="admin_settings")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, admin_text, reply_markup=keyboard)

@bot.message_handler(commands=['users'])
def users_command(message):
    """View all users"""
    user_id = str(message.from_user.id)
    
    # Check admin access
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
        
        response += f"<code>{uid}</code>\n"
        response += f"  👤 {username}\n"
        response += f"  👑 {is_admin}\n\n"
    
    response += f"Total: {len(users)} users"
    
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['addmsg'])
def addmsg_command(message):
    """Add message"""
    msg = bot.send_message(message.chat.id, "✍️ Send message (use {target} for target):")
    bot.register_next_step_handler(msg, process_new_message)

def process_new_message(message):
    new_message = message.text
    custom_messages.append(new_message)
    save_messages()
    
    bot.send_message(message.chat.id, f"✅ Added!\nTotal: {len(custom_messages)}")

@bot.message_handler(commands=['listmsg'])
def listmsg_command(message):
    """List messages"""
    if not custom_messages:
        bot.send_message(message.chat.id, "📭 No messages!")
        return
    
    response = "📋 <b>Messages:</b>\n\n"
    for i, msg in enumerate(custom_messages, 1):
        preview = msg[:50] + "..." if len(msg) > 50 else msg
        response += f"{i}. {preview}\n"
    
    response += f"\nTotal: {len(custom_messages)}"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="🗑️ Delete", callback_data="delete_msg_menu"),
        InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, response, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "delete_msg_menu")
def delete_msg_menu_callback(call):
    """Delete message menu"""
    if not custom_messages:
        bot.answer_callback_query(call.id, "No messages!")
        return
    
    keyboard = InlineKeyboardMarkup()
    for i in range(min(10, len(custom_messages))):  # Show first 10
        preview = custom_messages[i][:20] + "..." if len(custom_messages[i]) > 20 else custom_messages[i]
        keyboard.add(InlineKeyboardButton(text=f"❌ {preview}", callback_data=f"delete_msg_{i}"))
    
    keyboard.add(InlineKeyboardButton(text="◀️ Back", callback_data="list_msg"))
    
    bot.edit_message_text(
        "🗑️ Delete:",
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
            custom_messages.pop(index)
            save_messages()
            bot.answer_callback_query(call.id, "✅ Deleted!")
            listmsg_command(call.message)
    except:
        bot.answer_callback_query(call.id, "❌ Error!")

@bot.message_handler(commands=['addsession'])
def addsession_command(message):
    """Add session"""
    msg = bot.send_message(message.chat.id, "🔑 Send Instagram sessionid:")
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
        
        bot.send_message(message.chat.id, f"""
✅ Session added!

Status: Valid
Time: {datetime.now().strftime("%H:%M:%S")}

Total valid: {len([s for s in instagram_sessions if s.get('status') == 'valid'])}
""")
    else:
        bot.send_message(message.chat.id, f"""
❌ Invalid session!

Error: {info}

But saving anyway for testing...
""")
        
        session_data = {
            "session_id": session_id,
            "username": "invalid",
            "status": "testing",
            "added": datetime.now().strftime("%H:%M:%S")
        }
        instagram_sessions.append(session_data)
        save_sessions()

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
            username = session.get('username', 'user')
            response += f"{i}. {username}\n"
    
    invalid_sessions = [s for s in instagram_sessions if s.get('status') != 'valid']
    if invalid_sessions:
        response += "\n❌ <b>Testing/Invalid:</b>\n"
        for i, session in enumerate(invalid_sessions, 1):
            username = session.get('username', 'user')
            response += f"{i}. {username}\n"
    
    response += f"\n📊 {len(valid_sessions)} valid, {len(invalid_sessions)} testing"
    
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
    """Delete session menu"""
    if not instagram_sessions:
        bot.answer_callback_query(call.id, "No sessions!")
        return
    
    keyboard = InlineKeyboardMarkup()
    for i in range(len(instagram_sessions)):
        username = instagram_sessions[i].get('username', 'session')
        keyboard.add(InlineKeyboardButton(text=f"❌ Delete {i+1}: {username}", callback_data=f"delete_session_{i}"))
    
    keyboard.add(InlineKeyboardButton(text="◀️ Back", callback_data="sessions"))
    
    bot.edit_message_text(
        "🗑️ Delete session:",
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
    """Setup"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="🎯 Target", callback_data="set_target"),
        InlineKeyboardButton(text="🔗 URL", callback_data="set_url")
    )
    keyboard.add(
        InlineKeyboardButton(text="⏱️ Delay", callback_data="set_delay"),
        InlineKeyboardButton(text="📊 Count", callback_data="set_count")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Menu", callback_data="main_menu")
    )
    
    current = f"""
⚙️ <b>Settings:</b>

🎯 Target: {current_settings['target'] or 'None'}
🔗 URL: {current_settings['dm_url'][:30] + '...' if current_settings['dm_url'] else 'None'}
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
    msg = bot.send_message(call.message.chat.id, "🔗 Send Instagram DM URL:\n\nExample: https://www.instagram.com/direct/t/123456789/")
    bot.register_next_step_handler(msg, process_url)

def process_url(message):
    url = message.text.strip()
    thread_id = get_thread_id_from_url(url)
    
    if thread_id:
        current_settings['dm_url'] = url
        bot.send_message(message.chat.id, f"✅ URL set!\nThread ID: {thread_id}")
    else:
        # Accept anyway for testing
        current_settings['dm_url'] = url
        bot.send_message(message.chat.id, "⚠️ Couldn't extract thread ID, but URL saved anyway.")

@bot.callback_query_handler(func=lambda call: call.data == "set_count")
def set_count_callback(call):
    msg = bot.send_message(call.message.chat.id, "📊 Send message count (1-10000):")
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
        InlineKeyboardButton(text="⚡ 0.5-1s (ULTRA)", callback_data="delay_0.5_1"),
        InlineKeyboardButton(text="🚀 1-2s (FAST)", callback_data="delay_1_2")
    )
    keyboard.add(
        InlineKeyboardButton(text="💨 2-3s (NORMAL)", callback_data="delay_2_3"),
        InlineKeyboardButton(text="🐢 3-5s (SAFE)", callback_data="delay_3_5")
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
    """Start spam - IMPROVED VERSION"""
    # Check requirements
    if not current_settings['target']:
        bot.send_message(message.chat.id, "❌ Set target first!")
        return
    
    if not current_settings['dm_url']:
        bot.send_message(message.chat.id, "❌ Set URL first!")
        return
    
    if not custom_messages:
        bot.send_message(message.chat.id, "❌ Add messages first!")
        return
    
    if not instagram_sessions:
        bot.send_message(message.chat.id, "❌ Add sessions first!")
        return
    
    thread_id = get_thread_id_from_url(current_settings['dm_url'])
    if not thread_id:
        # Try to use the URL as thread ID directly
        thread_id = current_settings['dm_url'].split('/')[-1].strip('/')
        if not thread_id or len(thread_id) < 5:
            bot.send_message(message.chat.id, "❌ Couldn't get thread ID from URL!")
            return
    
    global spam_active
    
    if spam_active:
        bot.send_message(message.chat.id, "⚠️ Already running!")
        return
    
    spam_active = True
    
    # Start spam
    thread = threading.Thread(
        target=spam_worker, 
        args=(message.chat.id, thread_id),
        daemon=True
    )
    thread.start()
    
    bot.send_message(message.chat.id, f"""
✅ <b>SPAM STARTED!</b>

🎯 Target: {current_settings['target']}
🔗 Thread: {thread_id}
📊 Messages: {len(custom_messages)}
👥 Sessions: {len(instagram_sessions)}
⏱️ Delay: {current_settings['delay_min']}-{current_settings['delay_max']}s
📝 Count: {current_settings['message_count']}

⚡ <b>ULTRA FAST MODE!</b>
""")

def spam_worker(chat_id, thread_id):
    """Spam worker - IMPROVED"""
    global spam_active, success_count, unsuccess_count
    
    # Use all sessions for now (even "testing" ones)
    available_sessions = instagram_sessions
    
    if not available_sessions:
        bot.send_message(chat_id, "❌ No sessions!")
        spam_active = False
        return
    
    counter = 0
    session_index = 0
    
    bot.send_message(chat_id, "⚡ Starting spam...")
    
    while spam_active and counter < current_settings['message_count']:
        try:
            # Get message
            msg = random.choice(custom_messages)
            formatted_msg = msg.replace("{target}", current_settings['target'])
            
            # Get session
            session = available_sessions[session_index % len(available_sessions)]
            session_id = session.get('session_id')
            
            # Try to send
            success, result = send_instagram_message_simple(session_id, thread_id, formatted_msg)
            
            counter += 1
            
            if success:
                with counter_lock:
                    success_count += 1
                status = f"✅ {counter}: Sent"
            else:
                with counter_lock:
                    unsuccess_count += 1
                status = f"❌ {counter}: {result}"
            
            # Show first 10 results
            if counter <= 10:
                bot.send_message(chat_id, status, disable_notification=True)
            
            # Show progress
            if counter % 20 == 0:
                success_rate = (success_count/(counter))*100 if counter > 0 else 0
                bot.send_message(
                    chat_id,
                    f"📊 Progress: {counter}/{current_settings['message_count']}\n"
                    f"✅ {success_count} | ❌ {unsuccess_count}\n"
                    f"📈 {success_rate:.1f}% success",
                    disable_notification=True
                )
            
            # Next session
            session_index += 1
            
            # Delay
            delay = random.uniform(current_settings['delay_min'], current_settings['delay_max'])
            time.sleep(delay)
            
        except Exception as e:
            print(f"Spam error: {e}")
            time.sleep(1)
    
    # Done
    spam_active = False
    
    # Final report
    total = success_count + unsuccess_count
    success_rate = (success_count/total)*100 if total > 0 else 0
    
    bot.send_message(chat_id, f"""
✅ SPAM COMPLETE!

📊 Final:
• Sent: {counter}
• ✅ Success: {success_count}
• ❌ Failed: {unsuccess_count}
• 📈 Rate: {success_rate:.1f}%

{'⚠️ NO MESSAGES SENT!' if success_count == 0 else '🎉 SOME MESSAGES SENT!'}
""")

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
    """Stats"""
    total = success_count + unsuccess_count
    success_rate = (success_count/total)*100 if total > 0 else 0
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    stats_text = f"""
📊 <b>STATS</b>

✅ Success: {success_count}
❌ Failed: {unsuccess_count}
📈 Rate: {success_rate:.1f}%

💬 Messages: {len(custom_messages)}
👥 Sessions: {valid_sessions} valid

🎯 Target: {current_settings['target'] or 'None'}
🔗 URL: {'Set' if current_settings['dm_url'] else 'None'}

⏱️ Delay: {current_settings['delay_min']}-{current_settings['delay_max']}s
📝 Target: {current_settings['message_count']}

🔴 Status: {'ACTIVE' if spam_active else 'INACTIVE'}
"""
    
    bot.send_message(message.chat.id, stats_text)

@bot.message_handler(commands=['reset'])
def reset_command(message):
    """Reset"""
    global success_count, unsuccess_count
    
    success_count = 0
    unsuccess_count = 0
    bot.send_message(message.chat.id, "🔄 Reset!")

# ========== CALLBACK HANDLERS ==========
@bot.callback_query_handler(func=lambda call: call.data == "main_menu")
def main_menu_callback(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    send_start_message(call.message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_panel")
def admin_panel_callback(call):
    admin_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "admin_view_users")
def admin_view_users_callback(call):
    users_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data in ["admin_stats", "admin_broadcast", "admin_settings"])
def admin_other_callback(call):
    bot.answer_callback_query(call.id, "Feature coming soon!")

@bot.callback_query_handler(func=lambda call: call.data == "add_msg")
def add_msg_callback(call):
    msg = bot.send_message(call.message.chat.id, "✍️ Send message:")
    bot.register_next_step_handler(msg, process_new_message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "list_msg")
def list_msg_callback(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    listmsg_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "add_session")
def add_session_callback(call):
    msg = bot.send_message(call.message.chat.id, "🔑 Send sessionid:")
    bot.register_next_step_handler(msg, process_new_session)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "list_sessions")
def list_sessions_callback(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    sessions_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "setup")
def setup_callback(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    setup_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "start_spam")
def start_spam_callback(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    start_spam_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "stop_spam")
def stop_spam_callback(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    stop_spam_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "stats")
def stats_callback(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass
    stats_command(call.message)

# ========== MAIN ==========
if __name__ == "__main__":
    print(print_banner())
    print(f"🤖 Instagram Spam Bot v5.0 - WORKING VERSION")
    print(f"👑 Admin ID: {ADMIN_USER_ID}")
    print(f"💬 Messages: {len(custom_messages)}")
    print(f"🔑 Sessions: {len(instagram_sessions)}")
    
    try:
        bot_info = bot.get_me()
        print(f"✅ Bot: @{bot_info.username}")
        print("✅ Ready! Send /start")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        sys.exit(1)
    
    print("\n🚀 Starting bot...")
    bot.infinity_polling()
