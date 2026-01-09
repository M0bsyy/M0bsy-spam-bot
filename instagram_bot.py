import os
import sys
import json
import random
import time
import threading
import requests
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
    
    def check_access(self, user_id: str) -> bool:
        user_data = self.users.get(str(user_id))
        if not user_data:
            return True
        
        if user_data.get("is_admin", False):
            return True
        
        expiry_str = user_data.get("expiry", "")
        if not expiry_str:
            return True
        
        try:
            expiry = datetime.fromisoformat(expiry_str)
            if datetime.now() > expiry:
                user_data["active"] = False
                self.save_users()
                return False
        except:
            return True
        
        return user_data.get("active", True)
    
    def is_admin(self, user_id: str) -> bool:
        user_data = self.users.get(str(user_id))
        return user_data.get("is_admin", False) if user_data else False
    
    def get_all_users(self):
        return self.users
    
    def delete_user(self, user_id: str):
        if str(user_id) in self.users:
            del self.users[str(user_id)]
            self.save_users()
            return True
        return False
    
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
    "delay_min": 10,
    "delay_max": 30,
    "message_count": 100,
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

# ========== INSTAGRAM API FUNCTIONS ==========
def send_instagram_message(session_id, thread_id, message):
    """Send actual Instagram message"""
    try:
        headers = {
            'authority': 'www.instagram.com',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'cookie': f'sessionid={session_id}',
            'origin': 'https://www.instagram.com',
            'referer': f'https://www.instagram.com/direct/t/{thread_id}/',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36',
            'x-ig-app-id': '936619743392459',
            'x-ig-www-claim': '0'
        }
        
        # Generate unique client context
        client_context = str(int(time.time() * 1000)) + str(random.randint(1000, 9999))
        
        data = {
            'action': 'send_item',
            'client_context': client_context,
            'thread_ids': f'["{thread_id}"]',
            'item_type': 'text',
            'text': message
        }
        
        response = requests.post(
            'https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/',
            headers=headers,
            data=data,
            timeout=30
        )
        
        if response.status_code == 200:
            return True, "Message sent successfully"
        else:
            return False, f"API Error {response.status_code}: {response.text[:200]}"
            
    except requests.exceptions.Timeout:
        return False, "Timeout: Instagram server didn't respond"
    except requests.exceptions.ConnectionError:
        return False, "Connection error: Check internet connection"
    except Exception as e:
        return False, f"Error: {str(e)}"

def validate_instagram_session(session_id):
    """Check if Instagram session is valid"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Mobile Safari/537.36',
            'x-ig-app-id': '936619743392459'
        }
        
        response = requests.get(
            'https://www.instagram.com/api/v1/users/web_profile_info/?username=instagram',
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and 'user' in data['data']:
                username = data['data']['user']['username']
                return True, username, "Session valid"
        
        return False, None, f"Invalid session (HTTP {response.status_code})"
        
    except Exception as e:
        return False, None, f"Validation error: {str(e)}"

def get_thread_id_from_url(url):
    """Extract thread ID from Instagram DM URL"""
    try:
        url = url.strip()
        if '/direct/t/' in url:
            # Format: https://www.instagram.com/direct/t/THREAD_ID/
            parts = url.split('/direct/t/')
            if len(parts) > 1:
                thread_id = parts[1].strip('/').split('/')[0]
                if thread_id and len(thread_id) > 5:
                    return thread_id
        
        # Try to extract from any format
        import re
        patterns = [
            r'direct/t/([^/]+)',
            r't=([^&]+)',
            r'thread_([^_]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                thread_id = match.group(1)
                if len(thread_id) > 5:
                    return thread_id
        
        return None
    except:
        return None

# ========== INITIALIZE ADMIN ==========
user_manager = UserManager()

# Force add admin user on startup
def initialize_admin():
    """Ensure admin user exists and is set as admin"""
    admin_id = str(ADMIN_USER_ID)
    
    if admin_id not in user_manager.users:
        # Create admin user if doesn't exist
        user_manager.users[admin_id] = {
            "username": "Admin",
            "plan": "lifetime",
            "expiry": (datetime.now() + timedelta(days=36500)).isoformat(),
            "joined": datetime.now().isoformat(),
            "active": True,
            "is_admin": True
        }
        print(f"✅ Admin user created: {admin_id}")
    else:
        # Ensure existing user is admin
        user_manager.users[admin_id]["is_admin"] = True
        print(f"✅ Admin status set for user: {admin_id}")
    
    user_manager.save_users()

# Initialize admin on startup
initialize_admin()

# ========== HELPER FUNCTIONS ==========
def print_banner():
    banner = """
╔════════════════════════════════════════════╗
║        INSTAGRAM SPAM BOT v3.0             ║
║      (30 Days Free for Everyone)           ║
╚════════════════════════════════════════════╝
    """
    return banner

def send_start_message(chat_id):
    """Send welcome message with instructions"""
    user_id = str(chat_id)
    is_admin = user_manager.is_admin(user_id)
    
    welcome_text = f"""
{print_banner()}

📋 <b>Available Commands:</b>

🔹 /start - Show this help message
🔹 /addmsg - Add a new message for spamming
🔹 /listmsg - List all saved messages
🔹 /setup - Configure spam settings
🔹 /sessions - View/Manage Instagram sessions
🔹 /addsession - Add new Instagram session
🔹 /start_spam - Begin sending messages
🔹 /stop_spam - Stop sending messages
🔹 /stats - Show current statistics
🔹 /reset - Reset all counters

{"🔹 /admin - Admin Panel (Admin Only)" if is_admin else ""}

📊 <b>Current Status:</b>
• Messages saved: {len(custom_messages)}
• Valid Sessions: {len([s for s in instagram_sessions if s.get('status') == 'valid'])}
• Target: {current_settings['target'] or 'Not set'}
• Group URL: {'✅ Set' if current_settings['dm_url'] else '❌ Not set'}
• Spam Status: {'🟢 ACTIVE' if spam_active else '🔴 INACTIVE'}
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
    
    # Add user if not exists (regular user)
    if user_id != ADMIN_USER_ID:
        user_manager.add_user(user_id, username)
    
    send_start_message(message.chat.id)

@bot.message_handler(commands=['admin'])
def admin_command(message):
    """Admin panel command"""
    user_id = str(message.from_user.id)
    
    # Direct check for admin ID
    if user_id == ADMIN_USER_ID:
        # Force set as admin
        user_manager.set_admin(user_id, True)
    elif not user_manager.is_admin(user_id):
        bot.send_message(message.chat.id, "❌ You are not authorized to use admin commands!")
        return
    
    admin_text = """
🔐 <b>Admin Panel</b>

📊 <b>Admin Commands:</b>

👥 <b>User Management:</b>
• /users - View all users
• /addadmin [user_id] - Make user admin
• /removeadmin [user_id] - Remove admin
• /deleteuser [user_id] - Delete user

⚙️ <b>Bot Management:</b>
• /broadcast [message] - Send message to all users
• /stats_all - Show detailed statistics
• /cleanup - Clean old data

📁 <b>Data Management:</b>
• /backup - Create backup
• /restore - Restore from backup
• /reset_all - Reset all data
"""
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="👥 View All Users", callback_data="admin_view_users"),
        InlineKeyboardButton(text="📊 Bot Statistics", callback_data="admin_stats")
    )
    keyboard.add(
        InlineKeyboardButton(text="📢 Send Broadcast", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="🗑️ Cleanup Data", callback_data="admin_cleanup")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, admin_text, reply_markup=keyboard)

@bot.message_handler(commands=['users'])
def users_command(message):
    """View all users (Admin only)"""
    user_id = str(message.from_user.id)
    
    # Check if admin
    if user_id != ADMIN_USER_ID and not user_manager.is_admin(user_id):
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    users = user_manager.get_all_users()
    if not users:
        bot.send_message(message.chat.id, "📭 No users found!")
        return
    
    response = "👥 <b>All Users:</b>\n\n"
    for uid, data in users.items():
        username = data.get('username', 'Unknown')
        plan = data.get('plan', 'N/A')
        is_admin = "✅" if data.get('is_admin') else "❌"
        active = "🟢" if data.get('active', True) else "🔴"
        
        response += f"{active} ID: <code>{uid}</code>\n"
        response += f"   👤: {username}\n"
        response += f"   👑 Admin: {is_admin}\n"
        response += f"   📅 Plan: {plan}\n\n"
    
    response += f"Total: {len(users)} users"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="➕ Make Admin", callback_data="admin_add_admin"),
        InlineKeyboardButton(text="➖ Remove Admin", callback_data="admin_remove_admin")
    )
    keyboard.add(
        InlineKeyboardButton(text="🗑️ Delete User", callback_data="admin_delete_user"),
        InlineKeyboardButton(text="◀️ Back to Admin", callback_data="admin_panel")
    )
    
    bot.send_message(message.chat.id, response, reply_markup=keyboard)

@bot.message_handler(commands=['addmsg'])
def addmsg_command(message):
    """Add a new message for spamming"""
    msg = bot.send_message(message.chat.id, "✍️ Please send the message you want to add for spamming.\n\nYou can use {target} as a placeholder for the target name:")
    bot.register_next_step_handler(msg, process_new_message)

def process_new_message(message):
    new_message = message.text
    custom_messages.append(new_message)
    save_messages()
    
    bot.send_message(message.chat.id, f"✅ Message added successfully!\n\nTotal messages: {len(custom_messages)}\n\n📝 Preview:\n{new_message[:200]}")
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="➕ Add Another", callback_data="add_msg"),
        InlineKeyboardButton(text="📋 View All", callback_data="list_msg")
    )
    keyboard.add(
        InlineKeyboardButton(text="⚙️ Setup Spam", callback_data="setup")
    )
    bot.send_message(message.chat.id, "What would you like to do next?", reply_markup=keyboard)

@bot.message_handler(commands=['listmsg'])
def listmsg_command(message):
    """List all saved messages"""
    if not custom_messages:
        bot.send_message(message.chat.id, "📭 No messages saved yet. Use /addmsg to add messages.")
        return
    
    response = "📋 <b>Saved Messages:</b>\n\n"
    for i, msg in enumerate(custom_messages, 1):
        preview = msg[:50] + "..." if len(msg) > 50 else msg
        response += f"{i}. <code>{preview}</code>\n"
    
    response += f"\nTotal: {len(custom_messages)} messages"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="🗑️ Delete Message", callback_data="delete_msg_menu"),
        InlineKeyboardButton(text="✏️ Edit Message", callback_data="edit_msg_menu")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, response, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "delete_msg_menu")
def delete_msg_menu_callback(call):
    """Show delete message menu"""
    if not custom_messages:
        bot.answer_callback_query(call.id, "No messages to delete!")
        return
    
    keyboard = InlineKeyboardMarkup()
    for i in range(len(custom_messages)):
        preview = custom_messages[i][:30] + "..." if len(custom_messages[i]) > 30 else custom_messages[i]
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
            
            bot.answer_callback_query(call.id, f"✅ Message deleted!")
            
            # Show updated list
            listmsg_command(call.message)
    except:
        bot.answer_callback_query(call.id, "❌ Error deleting message!")

@bot.message_handler(commands=['addsession'])
def addsession_command(message):
    """Add new Instagram session"""
    msg = bot.send_message(message.chat.id, "🔑 Please send your Instagram session ID:\n\nTo get session ID:\n1. Login to Instagram in browser\n2. Open developer tools (F12)\n3. Go to Application → Cookies\n4. Copy 'sessionid' value\n\nSend 'cancel' to cancel.")
    bot.register_next_step_handler(msg, process_new_session)

def process_new_session(message):
    if message.text.lower() == 'cancel':
        bot.send_message(message.chat.id, "❌ Session addition cancelled.")
        return
    
    session_id = message.text.strip()
    
    if not session_id or len(session_id) < 10:
        bot.send_message(message.chat.id, "❌ Invalid session ID. Please check and try again.")
        return
    
    # Validate session
    bot.send_message(message.chat.id, "🔍 Validating Instagram session... Please wait.")
    
    valid, username, message_info = validate_instagram_session(session_id)
    
    if valid:
        session_data = {
            "session_id": session_id,
            "username": username,
            "status": "valid",
            "validated": datetime.now().isoformat(),
            "added_on": datetime.now().isoformat()
        }
        instagram_sessions.append(session_data)
        save_sessions()
        
        bot.send_message(message.chat.id, f"""
✅ <b>Session Added Successfully!</b>

👤 Username: @{username}
🔑 Status: ✅ Valid
📅 Added: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📊 Total valid sessions: {len([s for s in instagram_sessions if s.get('status') == 'valid'])}
""")
    else:
        # Still add but mark as invalid
        session_data = {
            "session_id": session_id,
            "username": "Unknown (Invalid)",
            "status": "invalid",
            "error": message_info,
            "added_on": datetime.now().isoformat()
        }
        instagram_sessions.append(session_data)
        save_sessions()
        
        bot.send_message(message.chat.id, f"""
⚠️ <b>Session Added (But Invalid)</b>

❌ Status: Invalid
📝 Error: {message_info}

⚠️ This session can't send messages until fixed.
Please check your session ID and try again.
""")

@bot.message_handler(commands=['sessions'])
def sessions_command(message):
    """View/Manage Instagram sessions"""
    if not instagram_sessions:
        bot.send_message(message.chat.id, "🔐 No Instagram sessions saved. Use /addsession to add one.")
        return
    
    valid_sessions = [s for s in instagram_sessions if s.get('status') == 'valid']
    invalid_sessions = [s for s in instagram_sessions if s.get('status') != 'valid']
    
    response = "👥 <b>Instagram Sessions:</b>\n\n"
    
    if valid_sessions:
        response += "✅ <b>Valid Sessions:</b>\n"
        for i, session in enumerate(valid_sessions, 1):
            username = session.get('username', 'Unknown')
            added = session.get('added_on', '').split('T')[0] if session.get('added_on') else 'Unknown'
            
            response += f"{i}. @{username}\n"
            response += f"   📅 Added: {added}\n"
            response += f"   🔑 ID: {session.get('session_id', '')[:15]}...\n\n"
    
    if invalid_sessions:
        response += "❌ <b>Invalid Sessions:</b>\n"
        for i, session in enumerate(invalid_sessions, 1):
            username = session.get('username', 'Unknown')
            error = session.get('error', 'Unknown error')[:50]
            
            response += f"{i}. {username}\n"
            response += f"   ⚠️ Error: {error}\n\n"
    
    response += f"\n📊 Summary: {len(valid_sessions)} valid, {len(invalid_sessions)} invalid"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="➕ Add Session", callback_data="add_session"),
        InlineKeyboardButton(text="🗑️ Delete Session", callback_data="delete_session_menu")
    )
    keyboard.add(
        InlineKeyboardButton(text="🔄 Validate All", callback_data="validate_sessions"),
        InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")
    )
    
    bot.send_message(message.chat.id, response, reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "delete_session_menu")
def delete_session_menu_callback(call):
    """Show delete session menu"""
    if not instagram_sessions:
        bot.answer_callback_query(call.id, "No sessions to delete!")
        return
    
    keyboard = InlineKeyboardMarkup()
    for i in range(len(instagram_sessions)):
        username = instagram_sessions[i].get('username', 'Unknown')
        status = "✅" if instagram_sessions[i].get('status') == 'valid' else "❌"
        keyboard.add(InlineKeyboardButton(text=f"{status} Delete: {username}", callback_data=f"delete_session_{i}"))
    
    keyboard.add(InlineKeyboardButton(text="◀️ Back", callback_data="sessions"))
    
    bot.edit_message_text(
        "🗑️ <b>Select session to delete:</b>",
        call.message.chat.id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_session_"))
def delete_session_callback(call):
    """Delete selected session"""
    try:
        index = int(call.data.split("_")[2])
        if 0 <= index < len(instagram_sessions):
            deleted_session = instagram_sessions.pop(index)
            save_sessions()
            
            bot.answer_callback_query(call.id, f"✅ Session deleted!")
            
            # Show updated list
            sessions_command(call.message)
    except:
        bot.answer_callback_query(call.id, "❌ Error deleting session!")

@bot.message_handler(commands=['setup'])
def setup_command(message):
    """Configure spam settings"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="🎯 Set Target Name", callback_data="set_target"),
        InlineKeyboardButton(text="🔗 Set Group URL", callback_data="set_url")
    )
    keyboard.add(
        InlineKeyboardButton(text="⏱️ Set Delay", callback_data="set_delay"),
        InlineKeyboardButton(text="📊 Set Message Count", callback_data="set_count")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")
    )
    
    current_status = f"""
⚙️ <b>Current Settings:</b>

🎯 Target: {current_settings['target'] or 'Not set'}
🔗 Group URL: {'✅ Set' if current_settings['dm_url'] else '❌ Not set'}
⏱️ Delay: {current_settings['delay_min']}-{current_settings['delay_max']} seconds
📊 Message Count: {current_settings['message_count']}
"""
    
    bot.send_message(message.chat.id, current_status + "\nConfigure your spam settings:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "set_count")
def set_count_callback(call):
    """Set message count"""
    msg = bot.send_message(call.message.chat.id, "📊 Enter total number of messages to send:")
    bot.register_next_step_handler(msg, process_message_count)

def process_message_count(message):
    try:
        count = int(message.text)
        if 1 <= count <= 10000:
            current_settings['message_count'] = count
            bot.send_message(message.chat.id, f"✅ Message count set to: {count}")
        else:
            bot.send_message(message.chat.id, "❌ Please enter a number between 1 and 10000")
    except:
        bot.send_message(message.chat.id, "❌ Please enter a valid number!")

@bot.message_handler(commands=['start_spam'])
def start_spam_command(message):
    """Begin sending messages"""
    # Check prerequisites
    checks = []
    
    if not current_settings['target']:
        checks.append("❌ Please set target first using /setup")
    
    if not current_settings['dm_url']:
        checks.append("❌ Please set Group URL first using /setup")
    
    if not custom_messages:
        checks.append("❌ No messages to send! Use /addmsg to add messages.")
    
    valid_sessions = [s for s in instagram_sessions if s.get('status') == 'valid']
    if not valid_sessions:
        checks.append("❌ No valid Instagram sessions! Use /addsession to add valid sessions.")
    
    if checks:
        bot.send_message(message.chat.id, "\n".join(checks))
        return
    
    # Get thread ID
    thread_id = get_thread_id_from_url(current_settings['dm_url'])
    if not thread_id:
        bot.send_message(message.chat.id, "❌ Invalid Instagram DM URL!\n\nFormat should be: https://www.instagram.com/direct/t/THREAD_ID/\n\nGet the URL from your Instagram DM.")
        return
    
    global spam_active, spam_threads
    
    if spam_active:
        bot.send_message(message.chat.id, "⚠️ Spam is already running! Use /stop_spam first.")
        return
    
    spam_active = True
    
    # Start spam thread
    thread = threading.Thread(
        target=spam_worker, 
        args=(message.chat.id, thread_id, 0)
    )
    thread.daemon = True
    thread.start()
    spam_threads.append(thread)
    
    bot.send_message(message.chat.id, f"""
✅ <b>Spam Started!</b>

🎯 Target: <code>{current_settings['target']}</code>
🔗 Thread ID: <code>{thread_id}</code>
📊 Messages: {len(custom_messages)} available
⏱️ Delay: {current_settings['delay_min']}-{current_settings['delay_max']} seconds
👥 Valid Accounts: {len(valid_sessions)}

📈 Now sending ACTUAL Instagram messages...

⚠️ <i>Warning: Sending too many messages may get accounts banned.
Use reasonable delays (10-30 seconds recommended).</i>

To stop, use /stop_spam
""")

def spam_worker(chat_id, thread_id, worker_id):
    """Background worker that sends REAL Instagram messages"""
    global spam_active, success_count, unsuccess_count
    
    # Get valid sessions
    valid_sessions = [s for s in instagram_sessions if s.get('status') == 'valid']
    if not valid_sessions:
        bot.send_message(chat_id, "❌ No valid sessions available!")
        spam_active = False
        return
    
    counter = 0
    session_index = 0
    
    bot.send_message(chat_id, f"""
🔄 Starting spam operation...

🎯 Target: {current_settings['target']}
🔗 Thread ID: {thread_id}
👥 Using {len(valid_sessions)} accounts
📊 Target messages: {current_settings['message_count']}
""")
    
    while spam_active and counter < current_settings.get('message_count', 100):
        try:
            # Select random message
            msg = random.choice(custom_messages)
            formatted_msg = msg.replace("{target}", current_settings['target'])
            
            # Select session
            session_data = valid_sessions[session_index % len(valid_sessions)]
            session_id = session_data.get('session_id', '')
            username = session_data.get('username', 'Unknown')
            
            # Send actual Instagram message
            success, result = send_instagram_message(session_id, thread_id, formatted_msg)
            
            counter += 1
            
            if success:
                with counter_lock:
                    success_count += 1
                status = f"✅ Msg {counter}: Sent via @{username}"
            else:
                with counter_lock:
                    unsuccess_count += 1
                status = f"❌ Msg {counter}: Failed ({result[:50]}) via @{username}"
            
            # Log every message during initial testing
            if counter <= 20:
                bot.send_message(chat_id, status, disable_notification=True)
            
            # Send progress update every 10 messages
            if counter % 10 == 0:
                bot.send_message(
                    chat_id,
                    f"📊 Progress: {counter}/{current_settings['message_count']}\n"
                    f"✅ Success: {success_count}\n"
                    f"❌ Failed: {unsuccess_count}\n"
                    f"📈 Success rate: {(success_count/counter*100 if counter > 0 else 0):.1f}%",
                    disable_notification=True
                )
            
            # Rotate to next session
            session_index += 1
            
            # Random delay between messages
            delay = random.uniform(current_settings['delay_min'], current_settings['delay_max'])
            time.sleep(delay)
            
        except Exception as e:
            error_msg = f"❌ Error in spam worker: {str(e)}"
            print(error_msg)
            bot.send_message(chat_id, error_msg[:1000])
            time.sleep(10)
    
    # Final report
    spam_active = False
    final_msg = f"""
✅ Spam completed!

📊 Final Statistics:
• Total attempted: {counter}
• Successfully sent: {success_count}
• Failed: {unsuccess_count}
• Success rate: {(success_count/counter*100 if counter > 0 else 0):.1f}%

🎯 Target: {current_settings['target']}
👥 Accounts used: {len(valid_sessions)}

<i>Note: Messages may take a few minutes to appear in Instagram.</i>
"""
    bot.send_message(chat_id, final_msg)

@bot.message_handler(commands=['stop_spam'])
def stop_spam_command(message):
    """Stop sending messages"""
    global spam_active
    
    if not spam_active:
        bot.send_message(message.chat.id, "⚠️ No active spam to stop!")
        return
    
    spam_active = False
    bot.send_message(message.chat.id, "🛑 Spam stopped! Current messages will finish sending.")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Show current statistics"""
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    stats_text = f"""
📊 <b>Current Statistics:</b>

✅ Successfully sent: {success_count}
❌ Failed: {unsuccess_count}
📈 Success rate: {(success_count/(success_count+unsuccess_count)*100 if (success_count+unsuccess_count) > 0 else 0):.1f}%

🎯 Target: {current_settings['target'] or 'Not set'}
🔗 Group URL: {'✅ Set' if current_settings['dm_url'] else '❌ Not set'}

💬 Messages available: {len(custom_messages)}
👥 Sessions: {valid_sessions} valid / {len(instagram_sessions)} total
📊 Spam Status: {'🟢 RUNNING' if spam_active else '🔴 STOPPED'}

⏱️ Delay: {current_settings['delay_min']}-{current_settings['delay_max']} seconds
📝 Target count: {current_settings['message_count']} messages

Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    bot.send_message(message.chat.id, stats_text)

@bot.message_handler(commands=['reset'])
def reset_command(message):
    """Reset all counters"""
    global success_count, unsuccess_count
    
    success_count = 0
    unsuccess_count = 0
    bot.send_message(message.chat.id, "🔄 Statistics reset to zero!")

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
    msg = bot.send_message(call.message.chat.id, "✍️ Please send the message you want to add for spamming.\n\nYou can use {target} as a placeholder for the target name:")
    bot.register_next_step_handler(msg, process_new_message)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data == "list_msg")
def list_msg_callback(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    listmsg_command(call.message)

@bot.callback_query_handler(func=lambda call: call.data == "add_session")
def add_session_callback(call):
    msg = bot.send_message(call.message.chat.id, "🔑 Please send your Instagram session ID:\n\nTo get session ID:\n1. Login to Instagram in browser\n2. Open developer tools (F12)\n3. Go to Application → Cookies\n4. Copy 'sessionid' value\n\nSend 'cancel' to cancel.")
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

@bot.callback_query_handler(func=lambda call: call.data == "set_target")
def set_target_callback(call):
    msg = bot.send_message(call.message.chat.id, "🎯 Please send the target username (will replace {target} in messages):")
    bot.register_next_step_handler(msg, process_target)
    bot.answer_callback_query(call.id)

def process_target(message):
    current_settings['target'] = message.text
    bot.send_message(message.chat.id, f"✅ Target set to: <code>{message.text}</code>")

@bot.callback_query_handler(func=lambda call: call.data == "set_url")
def set_url_callback(call):
    msg = bot.send_message(call.message.chat.id, "🔗 Please send the Instagram Group/DM URL:\n\nFormat: https://www.instagram.com/direct/t/THREAD_ID/\n\nGet this URL by opening the Instagram DM in browser.")
    bot.register_next_step_handler(msg, process_url)
    bot.answer_callback_query(call.id)

def process_url(message):
    url = message.text.strip()
    thread_id = get_thread_id_from_url(url)
    
    if thread_id:
        current_settings['dm_url'] = url
        bot.send_message(message.chat.id, f"✅ Group URL set!\n\nThread ID: <code>{thread_id}</code>")
    else:
        bot.send_message(message.chat.id, "❌ Invalid URL! Please send a valid Instagram DM URL.\n\nFormat: https://www.instagram.com/direct/t/THREAD_ID/")

@bot.callback_query_handler(func=lambda call: call.data == "set_delay")
def set_delay_callback(call):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="5-10 seconds (Fast)", callback_data="delay_5_10"),
        InlineKeyboardButton(text="10-20 seconds (Normal)", callback_data="delay_10_20")
    )
    keyboard.add(
        InlineKeyboardButton(text="20-30 seconds (Safe)", callback_data="delay_20_30"),
        InlineKeyboardButton(text="30-60 seconds (Very Safe)", callback_data="delay_30_60")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Back", callback_data="setup")
    )
    bot.send_message(call.message.chat.id, "⏱️ Select delay between messages (recommended: 10-30 seconds):", reply_markup=keyboard)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delay_"))
def process_delay_callback(call):
    data = call.data
    delays = data.split("_")[1:]
    current_settings['delay_min'] = int(delays[0])
    current_settings['delay_max'] = int(delays[1])
    
    bot.send_message(call.message.chat.id, f"✅ Delay set to {delays[0]}-{delays[1]} seconds")
    bot.answer_callback_query(call.id)

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

# ========== MAIN FUNCTION ==========
if __name__ == "__main__":
    print(print_banner())
    print(f"🤖 Instagram Spam Bot v3.0")
    print(f"👑 Admin User ID: {ADMIN_USER_ID}")
    print(f"💬 Messages loaded: {len(custom_messages)}")
    print(f"🔑 Sessions loaded: {len(instagram_sessions)}")
    
    # Initialize admin
    initialize_admin()
    
    try:
        bot_info = bot.get_me()
        print(f"✅ Bot username: @{bot_info.username}")
        print(f"✅ Bot is ready! Use /start in Telegram")
    except Exception as e:
        print(f"❌ Error connecting to Telegram: {e}")
        print("Please check your bot token and internet connection")
        sys.exit(1)
    
    print("\n⚠️ IMPORTANT SETUP STEPS:")
    print("1. Use /addsession to add Instagram session IDs")
    print("2. Use /setup to set target name and DM URL")
    print("3. Use /addmsg to add spam messages")
    print("4. Use /start_spam to begin sending\n")
    
    print("🚀 Starting bot polling...")
    bot.infinity_polling()
