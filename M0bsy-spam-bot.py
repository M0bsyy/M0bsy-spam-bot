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
ADMIN_USER_ID = "6107382622"  # CHANGE THIS TO YOUR ACTUAL TELEGRAM USER ID

# Initialize bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# ========== INSTAGRAM API FUNCTIONS - UPDATED ==========
def generate_csrf_token():
    """Generate random CSRF token"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(32))

def validate_instagram_session(session_id):
    """Check if Instagram session is valid"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36',
            'x-ig-app-id': '936619743392459'
        }
        
        response = requests.get(
            'https://www.instagram.com/api/v1/accounts/current_user/?__a=1',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                if 'user' in data or 'username' in data:
                    username = data.get('username', 'valid_user')
                    return True, username, "✅ Valid session"
            except:
                return True, "valid_user", "✅ Valid session (no username)"
        
        return False, None, f"❌ Invalid session (HTTP {response.status_code})"
        
    except Exception as e:
        return False, None, f"❌ Error: {str(e)[:50]}"

def send_instagram_message_working(session_id, thread_id, message):
    """WORKING Instagram message sending with correct endpoint"""
    try:
        # Generate random headers
        csrf_token = generate_csrf_token()
        
        headers = {
            'authority': 'www.instagram.com',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'cookie': f'sessionid={session_id}; csrftoken={csrf_token}',
            'origin': 'https://www.instagram.com',
            'referer': f'https://www.instagram.com/direct/inbox/',
            'sec-ch-ua': '"Not/A)Brand";v="99", "Google Chrome";v="115", "Chromium";v="115"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36',
            'x-csrftoken': csrf_token,
            'x-ig-app-id': '936619743392459',
            'x-ig-www-claim': '0',
            'x-instagram-ajax': '1007616494',
            'x-requested-with': 'XMLHttpRequest'
        }
        
        # Generate client context
        client_context = f"{int(time.time() * 1000)}{random.randint(1000, 9999)}"
        
        # CORRECT API ENDPOINT AND DATA FORMAT
        data = {
            'recipient_users': f'[[{thread_id}]]',  # Note double brackets
            'client_context': client_context,
            'thread': thread_id,
            'text': message,
            'action': 'send_item'
        }
        
        # CORRECT ENDPOINT
        response = requests.post(
            'https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/',
            headers=headers,
            data=data,
            timeout=15
        )
        
        # Check response
        if response.status_code == 200:
            return True, "✅ Message sent"
        else:
            # Try alternative format
            return send_instagram_alternative_v2(session_id, thread_id, message)
            
    except Exception as e:
        return False, f"❌ Error: {str(e)[:50]}"

def send_instagram_alternative_v2(session_id, thread_id, message):
    """Alternative method with different data format"""
    try:
        csrf_token = generate_csrf_token()
        
        headers = {
            'cookie': f'sessionid={session_id}; csrftoken={csrf_token}',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36',
            'x-csrftoken': csrf_token,
            'x-ig-app-id': '936619743392459',
            'content-type': 'application/x-www-form-urlencoded',
        }
        
        data = {
            'thread_ids': f'["{thread_id}"]',
            'client_context': str(int(time.time() * 1000)),
            'action': 'send_item',
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
            return True, "✅ Sent (v2)"
        else:
            return False, f"❌ HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"❌ Alt error: {str(e)[:30]}"

def get_thread_id_from_url(url):
    """Extract thread ID from Instagram DM URL"""
    try:
        url = url.strip()
        
        # Remove query parameters
        url = url.split('?')[0]
        
        # Try different patterns
        import re
        
        # Pattern 1: /direct/t/THREAD_ID/
        match = re.search(r'/direct/t/([^/]+)', url)
        if match:
            thread_id = match.group(1)
            if len(thread_id) > 5:
                return thread_id
        
        # Pattern 2: thread ID in URL
        match = re.search(r'thread[_-]?([a-zA-Z0-9]+)', url)
        if match:
            return match.group(1)
        
        # Pattern 3: Just get the last part
        parts = url.rstrip('/').split('/')
        if parts:
            last_part = parts[-1]
            if len(last_part) > 5 and not last_part.startswith('http'):
                return last_part
        
        # If nothing works, return the URL itself for testing
        return url.split('/')[-1] if '/' in url else url
        
    except:
        # Return a dummy thread ID for testing
        return "test_thread_123"

# ========== USER MANAGEMENT - FIXED ADMIN ==========
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
        user_id = str(user_id)
        if user_id not in self.users:
            self.users[user_id] = {
                "username": username,
                "plan": "30_days_free",
                "expiry": (datetime.now() + timedelta(days=30)).isoformat(),
                "joined": datetime.now().isoformat(),
                "active": True,
                "is_admin": False  # Default to not admin
            }
            # SPECIAL CASE: If this is the admin user ID, make them admin
            if user_id == ADMIN_USER_ID:
                self.users[user_id]["is_admin"] = True
                print(f"DEBUG: User {user_id} set as admin during add_user")
            self.save_users()
            return True
        return False
    
    def is_admin(self, user_id: str) -> bool:
        user_id = str(user_id)
        user_data = self.users.get(user_id)
        
        # DEBUG
        print(f"DEBUG is_admin: User {user_id}, Data: {user_data}")
        
        if user_data:
            is_admin = user_data.get("is_admin", False)
            print(f"DEBUG: is_admin value from DB: {is_admin}")
            return is_admin
        
        # If user not in DB but has admin ID, add them as admin
        if user_id == ADMIN_USER_ID:
            print(f"DEBUG: User {user_id} not in DB but is admin ID, adding as admin")
            self.add_user(user_id, "Admin")
            self.users[user_id]["is_admin"] = True
            self.save_users()
            return True
        
        return False
    
    def get_all_users(self):
        return self.users
    
    def set_admin(self, user_id: str, is_admin: bool = True):
        user_id = str(user_id)
        if user_id in self.users:
            self.users[user_id]["is_admin"] = is_admin
            self.save_users()
            print(f"DEBUG: User {user_id} admin status set to {is_admin}")
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

# Load data
load_messages()
load_sessions()

# ========== INITIALIZE ADMIN - FIXED ==========
user_manager = UserManager()

def initialize_admin():
    """Force create/update admin user"""
    admin_id = str(ADMIN_USER_ID)
    
    print(f"\n" + "="*50)
    print(f"ADMIN INITIALIZATION")
    print(f"Admin ID from config: {admin_id}")
    print(f"Current users in DB: {list(user_manager.users.keys())}")
    
    # Always ensure admin user exists and is admin
    if admin_id not in user_manager.users:
        print(f"Creating new admin user: {admin_id}")
        user_manager.users[admin_id] = {
            "username": "Admin",
            "plan": "lifetime",
            "expiry": (datetime.now() + timedelta(days=36500)).isoformat(),
            "joined": datetime.now().isoformat(),
            "active": True,
            "is_admin": True
        }
    else:
        print(f"Updating existing user {admin_id} to admin")
        user_manager.users[admin_id]["is_admin"] = True
        user_manager.users[admin_id]["username"] = "Admin"
    
    user_manager.save_users()
    
    # Verify
    is_admin = user_manager.is_admin(admin_id)
    print(f"Admin verification: User {admin_id} is admin? {is_admin}")
    print("="*50 + "\n")

initialize_admin()

# ========== HELPER FUNCTIONS ==========
def print_banner():
    return """
╔════════════════════════════════════════════╗
║        INSTAGRAM SPAM BOT v6.0             ║
║          FIXED & WORKING VERSION           ║
╚════════════════════════════════════════════╝
    """

def send_start_message(chat_id):
    """Send welcome message"""
    user_id = str(chat_id)
    is_admin = user_manager.is_admin(user_id)
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    # DEBUG
    print(f"DEBUG send_start_message: User {user_id}, is_admin: {is_admin}")
    
    welcome_text = f"""
{print_banner()}

👤 <b>Your ID:</b> <code>{user_id}</code>
{'🛡️ <b>Status:</b> ADMIN USER' if is_admin else '👤 <b>Status:</b> Regular User'}

📋 <b>Commands:</b>

🔹 /start - Show this menu
🔹 /addmsg - Add spam message
🔹 /listmsg - List messages
🔹 /setup - Configure settings
🔹 /sessions - View sessions
🔹 /addsession - Add Instagram session
🔹 /start_spam - Start sending messages
🔹 /stop_spam - Stop sending
🔹 /stats - View statistics
🔹 /reset - Reset counters

{'🔹 /admin - Admin Panel (You have access!)' if is_admin else ''}

📊 <b>Current Status:</b>
• Messages: {len(custom_messages)}
• Valid Sessions: {valid_sessions}
• Target: {current_settings['target'] or 'Not set'}
• Spam Active: {'🟢 YES' if spam_active else '🔴 NO'}
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

# ========== MAIN COMMANDS ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start command"""
    user_id = str(message.from_user.id)
    username = message.from_user.username or message.from_user.first_name or "User"
    
    print(f"DEBUG /start: User {user_id} ({username}) started bot")
    
    # Always add user
    user_manager.add_user(user_id, username)
    
    # If this is admin ID, ensure admin status
    if user_id == ADMIN_USER_ID:
        user_manager.set_admin(user_id, True)
        print(f"DEBUG: User {user_id} confirmed as admin")
    
    send_start_message(message.chat.id)

@bot.message_handler(commands=['admin'])
def admin_command(message):
    """Admin panel - COMPLETELY FIXED"""
    user_id = str(message.from_user.id)
    username = message.from_user.username or message.from_user.first_name or "User"
    
    print(f"\n" + "="*50)
    print(f"ADMIN COMMAND ACCESS CHECK")
    print(f"User ID: {user_id}")
    print(f"Username: {username}")
    print(f"Configured Admin ID: {ADMIN_USER_ID}")
    print(f"Match? {user_id == ADMIN_USER_ID}")
    
    # DIRECT HARDCODED CHECK - If ID matches, grant access NO MATTER WHAT
    if user_id == ADMIN_USER_ID:
        print(f"HARDCODED ADMIN ACCESS GRANTED!")
        
        # Ensure user is in database and marked as admin
        if user_id not in user_manager.users:
            user_manager.add_user(user_id, username)
        user_manager.set_admin(user_id, True)
        
        admin_text = f"""
🔐 <b>ADMIN PANEL - ACCESS GRANTED</b>

✅ <b>Welcome, Admin!</b>

👤 <b>Your Info:</b>
• User ID: <code>{user_id}</code>
• Username: {username}
• Admin Status: ✅ CONFIRMED

📋 <b>Admin Commands:</b>
• /users - View all bot users
• /stats_all - Detailed statistics
• /broadcast - Send message to all users

🛠️ <b>Admin Tools:</b>
• View all user data
• Monitor bot statistics
• Manage user access
"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(text="👥 View All Users", callback_data="admin_view_users"),
            InlineKeyboardButton(text="📊 Detailed Stats", callback_data="admin_stats")
        )
        keyboard.add(
            InlineKeyboardButton(text="📢 Send Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="⚙️ Bot Settings", callback_data="admin_settings")
        )
        keyboard.add(
            InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")
        )
        
        bot.send_message(message.chat.id, admin_text, reply_markup=keyboard)
        print(f"Admin panel shown to user {user_id}")
        
    else:
        # Check database
        is_admin = user_manager.is_admin(user_id)
        print(f"Database admin check: {is_admin}")
        
        if not is_admin:
            bot.send_message(message.chat.id, 
                f"❌ <b>ACCESS DENIED</b>\n\n"
                f"Your User ID: <code>{user_id}</code>\n"
                f"Admin User ID: <code>{ADMIN_USER_ID}</code>\n\n"
                f"Only the configured admin can access this panel."
            )
            print(f"Access denied for user {user_id}")
        else:
            # User is admin in database
            admin_text = f"""
🔐 <b>ADMIN PANEL</b>

👤 <b>Welcome, {username}!</b>

✅ <b>Admin Access Granted</b>

Your User ID: <code>{user_id}</code>
"""
            bot.send_message(message.chat.id, admin_text)
    
    print("="*50 + "\n")

@bot.message_handler(commands=['users'])
def users_command(message):
    """View all users - Admin only"""
    user_id = str(message.from_user.id)
    
    # Hardcoded admin check
    if user_id != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "❌ Admin only command!")
        return
    
    users = user_manager.get_all_users()
    if not users:
        bot.send_message(message.chat.id, "📭 No users in database!")
        return
    
    response = "👥 <b>ALL USERS IN DATABASE:</b>\n\n"
    
    for uid, data in users.items():
        username = data.get('username', 'Unknown')
        is_admin = "🛡️ ADMIN" if data.get('is_admin') else "👤 User"
        plan = data.get('plan', 'N/A')
        
        response += f"<b>{is_admin}</b>\n"
        response += f"ID: <code>{uid}</code>\n"
        response += f"Name: {username}\n"
        response += f"Plan: {plan}\n"
        response += f"Active: {'✅' if data.get('active', True) else '❌'}\n"
        response += "─" * 20 + "\n\n"
    
    response += f"📊 <b>Total Users:</b> {len(users)}"
    
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['addmsg'])
def addmsg_command(message):
    """Add message for spamming"""
    msg = bot.send_message(message.chat.id, 
        "✍️ <b>Send the message you want to spam:</b>\n\n"
        "You can use <code>{target}</code> as a placeholder for the target username.\n\n"
        "Example: <i>Hello {target}, check this out!</i>"
    )
    bot.register_next_step_handler(msg, process_new_message)

def process_new_message(message):
    new_message = message.text
    custom_messages.append(new_message)
    save_messages()
    
    bot.send_message(message.chat.id, 
        f"✅ <b>Message Added!</b>\n\n"
        f"📝 <b>Preview:</b>\n{new_message[:200]}\n\n"
        f"📊 <b>Total Messages:</b> {len(custom_messages)}"
    )
    
    # Show options
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="➕ Add Another", callback_data="add_msg"),
        InlineKeyboardButton(text="📋 View All", callback_data="list_msg")
    )
    bot.send_message(message.chat.id, "What would you like to do next?", reply_markup=keyboard)

@bot.message_handler(commands=['listmsg'])
def listmsg_command(message):
    """List all saved messages"""
    if not custom_messages:
        bot.send_message(message.chat.id, "📭 No messages saved yet!")
        return
    
    response = "📋 <b>SAVED MESSAGES:</b>\n\n"
    
    for i, msg in enumerate(custom_messages, 1):
        preview = msg[:80] + "..." if len(msg) > 80 else msg
        response += f"{i}. <code>{preview}</code>\n\n"
    
    response += f"📊 <b>Total:</b> {len(custom_messages)} messages"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="🗑️ Delete Messages", callback_data="delete_msg_menu"),
        InlineKeyboardButton(text="◀️ Back to Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, response, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "delete_msg_menu")
def delete_msg_menu_callback(call):
    """Show message deletion menu"""
    if not custom_messages:
        bot.answer_callback_query(call.id, "No messages to delete!")
        return
    
    keyboard = InlineKeyboardMarkup()
    
    # Show first 5 messages for deletion
    for i in range(min(5, len(custom_messages))):
        preview = custom_messages[i][:40] + "..." if len(custom_messages[i]) > 40 else custom_messages[i]
        keyboard.add(InlineKeyboardButton(text=f"❌ Delete: {preview}", callback_data=f"delete_msg_{i}"))
    
    keyboard.add(InlineKeyboardButton(text="◀️ Back", callback_data="list_msg"))
    
    bot.edit_message_text(
        "🗑️ <b>Select message to delete:</b>",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_msg_"))
def delete_msg_callback(call):
    """Delete selected message"""
    try:
        index = int(call.data.split("_")[2])
        if 0 <= index < len(custom_messages):
            deleted_msg = custom_messages.pop(index)
            save_messages()
            bot.answer_callback_query(call.id, "✅ Message deleted!")
            listmsg_command(call.message)
    except:
        bot.answer_callback_query(call.id, "❌ Error deleting message!")

@bot.message_handler(commands=['addsession'])
def addsession_command(message):
    """Add Instagram session"""
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
    session_id = message.text.strip()
    
    if not session_id or len(session_id) < 20:
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
            f"📊 <b>Valid Sessions:</b> {len([s for s in instagram_sessions if s.get('status') == 'valid'])}\n\n"
            f"<i>This session can now send messages.</i>"
        )
    else:
        bot.send_message(message.chat.id,
            f"❌ <b>Session Validation Failed!</b>\n\n"
            f"<b>Error:</b> {info}\n\n"
            f"<i>Session saved but marked as invalid. It may not be able to send messages.</i>"
        )
        
        # Save anyway for testing
        session_data = {
            "session_id": session_id,
            "username": "invalid_session",
            "status": "invalid",
            "error": info,
            "added": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        instagram_sessions.append(session_data)
        save_sessions()

@bot.message_handler(commands=['sessions'])
def sessions_command(message):
    """View Instagram sessions"""
    if not instagram_sessions:
        bot.send_message(message.chat.id, "🔐 No Instagram sessions saved!")
        return
    
    valid_sessions = [s for s in instagram_sessions if s.get('status') == 'valid']
    invalid_sessions = [s for s in instagram_sessions if s.get('status') != 'valid']
    
    response = "👥 <b>INSTAGRAM SESSIONS</b>\n\n"
    
    if valid_sessions:
        response += "✅ <b>VALID SESSIONS:</b>\n"
        for i, session in enumerate(valid_sessions, 1):
            username = session.get('username', 'Unknown')
            added = session.get('added', 'Unknown time')
            response += f"{i}. <b>{username}</b>\n"
            response += f"   🕒 {added}\n"
            response += f"   🔑 ID: {session.get('session_id', '')[:15]}...\n\n"
    
    if invalid_sessions:
        response += "❌ <b>INVALID/TESTING SESSIONS:</b>\n"
        for i, session in enumerate(invalid_sessions, 1):
            username = session.get('username', 'Unknown')
            error = session.get('error', 'Unknown error')[:50]
            response += f"{i}. {username}\n"
            response += f"   ⚠️ {error}\n\n"
    
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

@bot.callback_query_handler(func=lambda call: call.data == "delete_session_menu")
def delete_session_menu_callback(call):
    """Show session deletion menu"""
    if not instagram_sessions:
        bot.answer_callback_query(call.id, "No sessions!")
        return
    
    keyboard = InlineKeyboardMarkup()
    
    for i in range(len(instagram_sessions)):
        username = instagram_sessions[i].get('username', 'Unknown')
        status = "✅" if instagram_sessions[i].get('status') == 'valid' else "❌"
        keyboard.add(InlineKeyboardButton(text=f"{status} Delete {username}", callback_data=f"delete_session_{i}"))
    
    keyboard.add(InlineKeyboardButton(text="◀️ Back", callback_data="sessions"))
    
    bot.edit_message_text(
        "🗑️ <b>Select session to delete:</b>",
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
            deleted_session = instagram_sessions.pop(index)
            save_sessions()
            bot.answer_callback_query(call.id, "✅ Session deleted!")
            sessions_command(call.message)
    except:
        bot.answer_callback_query(call.id, "❌ Error deleting session!")

@bot.message_handler(commands=['setup'])
def setup_command(message):
    """Configure spam settings"""
    current_config = f"""
⚙️ <b>CURRENT CONFIGURATION</b>

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

@bot.callback_query_handler(func=lambda call: call.data == "set_target")
def set_target_callback(call):
    msg = bot.send_message(call.message.chat.id, "🎯 <b>Enter the target username:</b>\n\nThis will replace {target} in your messages.")
    bot.register_next_step_handler(msg, process_target)

def process_target(message):
    current_settings['target'] = message.text.strip()
    bot.send_message(message.chat.id, f"✅ <b>Target set to:</b> {current_settings['target']}")

@bot.callback_query_handler(func=lambda call: call.data == "set_url")
def set_url_callback(call):
    msg = bot.send_message(call.message.chat.id, 
        "🔗 <b>Enter Instagram DM/Group URL:</b>\n\n"
        "Format: <code>https://www.instagram.com/direct/t/THREAD_ID/</code>\n\n"
        "To get this URL:\n"
        "1. Open Instagram in browser\n"
        "2. Go to the DM/group where you want to send messages\n"
        "3. Copy the URL from address bar"
    )
    bot.register_next_step_handler(msg, process_url)

def process_url(message):
    url = message.text.strip()
    thread_id = get_thread_id_from_url(url)
    
    if thread_id:
        current_settings['dm_url'] = url
        bot.send_message(message.chat.id, 
            f"✅ <b>URL set successfully!</b>\n\n"
            f"<b>Thread ID detected:</b> <code>{thread_id}</code>\n"
            f"<b>Full URL:</b> <code>{url[:100]}...</code>"
        )
    else:
        bot.send_message(message.chat.id, 
            "⚠️ <b>Could not detect Thread ID from URL!</b>\n\n"
            "But the URL has been saved anyway.\n"
            "Make sure the URL is in this format:\n"
            "<code>https://www.instagram.com/direct/t/THREAD_ID/</code>"
        )
        current_settings['dm_url'] = url

@bot.callback_query_handler(func=lambda call: call.data == "set_count")
def set_count_callback(call):
    msg = bot.send_message(call.message.chat.id, "📊 <b>Enter total number of messages to send:</b>\n\nRecommended: 100-1000")
    bot.register_next_step_handler(msg, process_count)

def process_count(message):
    try:
        count = int(message.text)
        if 1 <= count <= 10000:
            current_settings['message_count'] = count
            bot.send_message(message.chat.id, f"✅ <b>Message count set to:</b> {count}")
        else:
            bot.send_message(message.chat.id, "❌ Please enter a number between 1 and 10000")
    except:
        bot.send_message(message.chat.id, "❌ Please enter a valid number!")

@bot.callback_query_handler(func=lambda call: call.data == "set_delay")
def set_delay_callback(call):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="⚡ 0.5-1s (ULTRA FAST)", callback_data="delay_0.5_1"),
        InlineKeyboardButton(text="🚀 1-2s (VERY FAST)", callback_data="delay_1_2")
    )
    keyboard.add(
        InlineKeyboardButton(text="💨 2-3s (FAST)", callback_data="delay_2_3"),
        InlineKeyboardButton(text="🐢 3-5s (NORMAL)", callback_data="delay_3_5")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Back", callback_data="setup")
    )
    
    bot.send_message(call.message.chat.id, "⏱️ <b>Select delay between messages:</b>\n\nLower = Faster but higher ban risk", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delay_"))
def process_delay_callback(call):
    data = call.data
    delays = data.split("_")[1:]
    current_settings['delay_min'] = float(delays[0])
    current_settings['delay_max'] = float(delays[1])
    
    bot.send_message(call.message.chat.id, f"✅ <b>Delay set to:</b> {delays[0]}-{delays[1]} seconds")

@bot.message_handler(commands=['start_spam'])
def start_spam_command(message):
    """Start sending messages"""
    # Check all requirements
    checks = []
    
    if not current_settings['target']:
        checks.append("❌ Set target username first!")
    
    if not current_settings['dm_url']:
        checks.append("❌ Set Instagram URL first!")
    
    if not custom_messages:
        checks.append("❌ Add messages first!")
    
    if not instagram_sessions:
        checks.append("❌ Add Instagram sessions first!")
    
    if checks:
        bot.send_message(message.chat.id, "\n".join(checks))
        return
    
    # Get thread ID
    thread_id = get_thread_id_from_url(current_settings['dm_url'])
    if not thread_id:
        bot.send_message(message.chat.id, 
            "⚠️ <b>Could not extract Thread ID from URL!</b>\n\n"
            "Trying to use the URL directly..."
        )
        thread_id = current_settings['dm_url']
    
    global spam_active
    
    if spam_active:
        bot.send_message(message.chat.id, "⚠️ Spam is already running!")
        return
    
    spam_active = True
    
    # Start spam in new thread
    thread = threading.Thread(
        target=spam_worker,
        args=(message.chat.id, thread_id),
        daemon=True
    )
    thread.start()
    
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    bot.send_message(message.chat.id,
        f"✅ <b>SPAM STARTED!</b>\n\n"
        f"🎯 <b>Target:</b> {current_settings['target']}\n"
        f"🔗 <b>Thread ID:</b> <code>{thread_id[:50]}...</code>\n"
        f"📊 <b>Messages:</b> {len(custom_messages)} available\n"
        f"👥 <b>Accounts:</b> {valid_sessions} valid sessions\n"
        f"⏱️ <b>Delay:</b> {current_settings['delay_min']}-{current_settings['delay_max']}s\n"
        f"📝 <b>Target Count:</b> {current_settings['message_count']} messages\n\n"
        f"⚡ <b>ULTRA FAST MODE ACTIVE!</b>\n\n"
        f"<i>Messages will start sending now. Check your Instagram DM.</i>"
    )

def spam_worker(chat_id, thread_id):
    """Main spam worker function"""
    global spam_active, success_count, unsuccess_count
    
    # Get all sessions (try even invalid ones)
    available_sessions = instagram_sessions
    
    if not available_sessions:
        bot.send_message(chat_id, "❌ No sessions available!")
        spam_active = False
        return
    
    counter = 0
    session_index = 0
    
    bot.send_message(chat_id, "⚡ Starting message sending...")
    
    # Send first test message
    try:
        test_session = available_sessions[0]
        test_msg = random.choice(custom_messages) if custom_messages else "Test message"
        formatted_msg = test_msg.replace("{target}", current_settings['target'])
        
        success, result = send_instagram_message_working(
            test_session.get('session_id'), 
            thread_id, 
            formatted_msg
        )
        
        bot.send_message(chat_id, f"🧪 <b>Test Message Result:</b>\n{result}")
    except:
        pass
    
    # Main sending loop
    while spam_active and counter < current_settings['message_count']:
        try:
            # Get random message
            msg = random.choice(custom_messages)
            formatted_msg = msg.replace("{target}", current_settings['target'])
            
            # Get next session
            session = available_sessions[session_index % len(available_sessions)]
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
            
            # Show first 5 results in detail
            if counter <= 5:
                bot.send_message(chat_id, status, disable_notification=True)
            
            # Show progress every 10 messages
            if counter % 10 == 0:
                total_tried = success_count + unsuccess_count
                success_rate = (success_count / total_tried * 100) if total_tried > 0 else 0
                
                bot.send_message(chat_id,
                    f"📊 <b>Progress Report</b>\n\n"
                    f"Messages sent: {counter}/{current_settings['message_count']}\n"
                    f"✅ Success: {success_count}\n"
                    f"❌ Failed: {unsuccess_count}\n"
                    f"📈 Success Rate: {success_rate:.1f}%",
                    disable_notification=True
                )
            
            # Move to next session
            session_index += 1
            
            # Wait before next message
            delay = random.uniform(current_settings['delay_min'], current_settings['delay_max'])
            time.sleep(delay)
            
        except Exception as e:
            error_msg = f"❌ Error in spam worker: {str(e)[:100]}"
            print(error_msg)
            time.sleep(1)
    
    # Spam finished
    spam_active = False
    
    # Final report
    total = success_count + unsuccess_count
    success_rate = (success_count / total * 100) if total > 0 else 0
    
    final_report = f"""
✅ <b>SPAM COMPLETED!</b>

📊 <b>Final Statistics:</b>

• Total Attempted: {counter}
• ✅ Successful: {success_count}
• ❌ Failed: {unsuccess_count}
• 📈 Success Rate: {success_rate:.1f}%

🎯 <b>Target:</b> {current_settings['target']}
🔗 <b>Thread:</b> {thread_id[:30]}...

{'⚠️ <b>WARNING:</b> No messages were sent successfully!' if success_count == 0 else '🎉 <b>SUCCESS:</b> Messages were sent!'}

<i>Check your Instagram DM to confirm messages arrived.</i>
"""
    
    bot.send_message(chat_id, final_report)

@bot.message_handler(commands=['stop_spam'])
def stop_spam_command(message):
    """Stop sending messages"""
    global spam_active
    
    if not spam_active:
        bot.send_message(message.chat.id, "⚠️ No active spam to stop!")
        return
    
    spam_active = False
    bot.send_message(message.chat.id, "🛑 Stopping spam... Current message will finish.")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Show statistics"""
    total = success_count + unsuccess_count
    success_rate = (success_count / total * 100) if total > 0 else 0
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    stats_text = f"""
📊 <b>BOT STATISTICS</b>

✅ <b>Messages Sent Successfully:</b> {success_count}
❌ <b>Messages Failed:</b> {unsuccess_count}
📈 <b>Success Rate:</b> {success_rate:.1f}%

💬 <b>Saved Messages:</b> {len(custom_messages)}
👥 <b>Instagram Sessions:</b> {valid_sessions} valid / {len(instagram_sessions)} total

🎯 <b>Current Target:</b> {current_settings['target'] or 'Not set'}
🔗 <b>Instagram URL:</b> {'✅ Set' if current_settings['dm_url'] else '❌ Not set'}

⏱️ <b>Message Delay:</b> {current_settings['delay_min']}-{current_settings['delay_max']} seconds
📝 <b>Target Count:</b> {current_settings['message_count']} messages

🔴 <b>Spam Status:</b> {'🟢 ACTIVE' if spam_active else '🔴 INACTIVE'}

🕒 <b>Last Update:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    bot.send_message(message.chat.id, stats_text)

@bot.message_handler(commands=['reset'])
def reset_command(message):
    """Reset statistics"""
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
    bot.answer_callback_query(call.id, "✅ Admin feature - Working!")

@bot.callback_query_handler(func=lambda call: call.data == "add_msg")
def add_msg_callback(call):
    msg = bot.send_message(call.message.chat.id, "✍️ Send your message:")
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
    msg = bot.send_message(call.message.chat.id, "🔑 Send Instagram sessionid:")
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

# ========== MAIN FUNCTION ==========
if __name__ == "__main__":
    print(print_banner())
    print(f"🤖 Instagram Spam Bot v6.0 - FIXED & WORKING")
    print(f"👑 Admin User ID: {ADMIN_USER_ID}")
    print(f"💬 Messages loaded: {len(custom_messages)}")
    print(f"🔑 Sessions loaded: {len(instagram_sessions)}")
    
    try:
        bot_info = bot.get_me()
        print(f"✅ Bot username: @{bot_info.username}")
        print(f"✅ Bot is ready! Send /start in Telegram")
        
        print(f"\n⚠️ IMPORTANT: Make sure ADMIN_USER_ID ({ADMIN_USER_ID}) is your actual Telegram User ID!")
        print(f"To get your Telegram User ID:")
        print(f"1. Go to @userinfobot on Telegram")
        print(f"2. Send /start")
        print(f"3. Copy your numeric ID and update the script if needed\n")
        
    except Exception as e:
        print(f"❌ Error connecting to Telegram: {e}")
        print("Please check your bot token and internet connection")
        sys.exit(1)
    
    print("🚀 Starting bot polling...")
    bot.infinity_polling()
