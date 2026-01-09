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
ADMIN_USER_ID = 6107382622  # YOUR CORRECT TELEGRAM USER ID

# Initialize bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# ========== INSTAGRAM API FUNCTIONS - FIXED ==========
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
        
        # Simple check - try to access Instagram with session
        response = requests.get(
            'https://www.instagram.com/accounts/edit/',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200 and 'instagram' in response.text.lower():
            # Try to extract username
            import re
            username_match = re.search(r'"username":"([^"]+)"', response.text)
            username = username_match.group(1) if username_match else "instagram_user"
            return True, username, "✅ Valid session"
        
        return False, None, f"❌ Invalid session (Not logged in)"
        
    except Exception as e:
        return False, None, f"❌ Error: {str(e)[:50]}"

def send_instagram_message(session_id, thread_id, message):
    """Send Instagram message - SIMPLIFIED WORKING VERSION"""
    try:
        # First, get CSRF token from Instagram
        csrf_token = extract_csrf_token(session_id)
        if not csrf_token:
            csrf_token = generate_csrf_token()
        
        headers = {
            'cookie': f'sessionid={session_id}; csrftoken={csrf_token}',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Mobile Safari/537.36',
            'x-csrftoken': csrf_token,
            'x-ig-app-id': '936619743392459',
            'content-type': 'application/x-www-form-urlencoded',
            'x-requested-with': 'XMLHttpRequest',
            'origin': 'https://www.instagram.com',
            'referer': 'https://www.instagram.com/direct/inbox/',
        }
        
        # Working data format (tested)
        data = {
            'recipient_users': f'[["{thread_id}"]]',
            'client_context': f"web:{int(time.time() * 1000)}:{random.randint(100, 999)}",
            'thread_ids': f'["{thread_id}"]',
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
            return True, "✅ Message sent successfully"
        elif response.status_code == 400:
            # Try alternative method
            return send_instagram_alternative(session_id, thread_id, message, csrf_token)
        else:
            return False, f"❌ HTTP {response.status_code}: {response.text[:100]}"
            
    except Exception as e:
        return False, f"❌ Error: {str(e)[:50]}"

def extract_csrf_token(session_id):
    """Extract actual CSRF token from Instagram"""
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
            import re
            match = re.search(r'"csrf_token":"([^"]+)"', response.text)
            if match:
                return match.group(1)
            
            # Alternative pattern
            match = re.search(r'csrf_token["\']?\s*[:=]\s*["\']([^"\']+)', response.text)
            if match:
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
        }
        
        # Different data format
        data = {
            'thread_id': thread_id,
            'client_context': str(int(time.time() * 1000)),
            'action': 'send_item',
            'item_type': 'raven_text',
            'text': message,
            'padding': ''
        }
        
        response = requests.post(
            'https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/',
            headers=headers,
            data=data,
            timeout=15
        )
        
        if response.status_code == 200:
            return True, "✅ Sent (alternative)"
        else:
            return False, f"❌ Alt HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"❌ Alt error: {str(e)[:30]}"

def get_thread_id_from_url(url):
    """Extract thread ID from Instagram URL"""
    try:
        url = url.strip()
        
        # Remove query parameters
        url = url.split('?')[0]
        
        # Extract from /direct/t/ format
        if '/direct/t/' in url:
            parts = url.split('/direct/t/')
            if len(parts) > 1:
                thread_id = parts[1].strip('/')
                if thread_id:
                    return thread_id
        
        # Try to get any long alphanumeric string at the end
        import re
        match = re.search(r'([a-zA-Z0-9_-]{10,})$', url)
        if match:
            return match.group(1)
        
        return None
    except:
        return None

# ========== USER MANAGEMENT - FIXED ADMIN SYSTEM ==========
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
        
        # HARDCODED CHECK - If user ID matches admin ID, grant access
        if user_id == str(ADMIN_USER_ID):
            print(f"✅ HARDCODED ADMIN ACCESS: User {user_id} is admin")
            return True
        
        user_data = self.users.get(user_id)
        if user_data:
            return user_data.get("is_admin", False)
        
        return False
    
    def get_all_users(self):
        return self.users
    
    def get_active_users(self):
        active_users = {}
        for uid, data in self.users.items():
            if data.get("active", True):
                active_users[uid] = data
        return active_users
    
    def set_admin(self, user_id: int, is_admin: bool = True):
        user_id = str(user_id)
        if user_id in self.users:
            self.users[user_id]["is_admin"] = is_admin
            self.save_users()
            return True
        return False
    
    def delete_user(self, user_id: int):
        user_id = str(user_id)
        if user_id in self.users:
            del self.users[user_id]
            self.save_users()
            return True
        return False
    
    def add_user_time(self, user_id: int, days: int):
        user_id = str(user_id)
        if user_id in self.users:
            expiry = datetime.now() + timedelta(days=days)
            self.users[user_id]["expiry"] = expiry.isoformat()
            self.users[user_id]["active"] = True
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

# Load data
load_messages()
load_sessions()

# ========== INITIALIZE ==========
user_manager = UserManager()

def initialize_admin():
    """Initialize admin user"""
    admin_id = str(ADMIN_USER_ID)
    
    print(f"\n{'='*50}")
    print(f"ADMIN INITIALIZATION")
    print(f"Admin User ID: {admin_id}")
    print(f"{'='*50}\n")
    
    # Ensure admin user exists
    user_manager.add_user(int(admin_id), "Admin")
    user_manager.set_admin(int(admin_id), True)

initialize_admin()

# ========== HELPER FUNCTIONS ==========
def print_banner():
    return """
╔════════════════════════════════════════════╗
║        INSTAGRAM SPAM BOT v7.0             ║
║          FULLY WORKING VERSION             ║
╚════════════════════════════════════════════╝
    """

def send_start_message(chat_id):
    """Send welcome message"""
    user_id = chat_id
    is_admin = user_manager.is_admin(user_id)
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    welcome_text = f"""
{print_banner()}

👤 <b>User ID:</b> <code>{user_id}</code>
{'🛡️ <b>Status:</b> ADMIN USER' if is_admin else '👤 <b>Status:</b> Regular User'}

📋 <b>MAIN COMMANDS:</b>

🔹 /start - Show this menu
🔹 /addmsg - Add spam message
🔹 /listmsg - List all messages
🔹 /setup - Configure settings
🔹 /sessions - View Instagram sessions
🔹 /addsession - Add Instagram session
🔹 /start_spam - Start sending messages
🔹 /stop_spam - Stop sending
🔹 /stats - View statistics
🔹 /reset - Reset counters
🔹 /help - Show all commands

{'🔹 /admin - Admin Panel (You have access!)' if is_admin else ''}

📊 <b>CURRENT STATUS:</b>
• Messages: {len(custom_messages)}
• Valid Sessions: {valid_sessions}
• Target: {current_settings['target'] or 'Not set'}
• Active: {'🟢 YES' if spam_active else '🔴 NO'}
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
    
    print(f"User {user_id} ({username}) started bot")
    
    # Add user to database
    user_manager.add_user(user_id, username)
    
    send_start_message(message.chat.id)

@bot.message_handler(commands=['help'])
def help_command(message):
    """Show help with all commands"""
    user_id = message.from_user.id
    is_admin = user_manager.is_admin(user_id)
    
    help_text = f"""
📚 <b>ALL COMMANDS:</b>

<b>Basic Commands:</b>
/start - Show main menu
/help - Show this help
/addmsg - Add spam message
/listmsg - List all messages
/setup - Configure settings
/sessions - View Instagram sessions
/addsession - Add Instagram session
/start_spam - Start sending messages
/stop_spam - Stop sending messages
/stats - View statistics
/reset - Reset counters

<b>Admin Commands:</b>
/admin - Admin control panel
/users - View all users
/addadmin [user_id] - Make user admin
/removeadmin [user_id] - Remove admin
/deleteuser [user_id] - Delete user
/broadcast [message] - Broadcast to all users
/addtime [user_id] [days] - Add time to user
/cleanup - Clean old data
/backup - Create backup
/restore - Restore from backup

<b>Current Admin Status:</b>
{'✅ YOU ARE ADMIN' if is_admin else '❌ You are not admin'}
"""
    
    bot.send_message(message.chat.id, help_text)

# ========== ADMIN COMMANDS - COMPLETE SET ==========
@bot.message_handler(commands=['admin'])
def admin_command(message):
    """Admin panel - FULLY WORKING"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or "User"
    
    # HARDCODED ADMIN CHECK - This will definitely work
    if user_id == ADMIN_USER_ID:
        admin_text = f"""
🔐 <b>ADMIN CONTROL PANEL</b>

✅ <b>Welcome, {username}!</b>
🆔 <b>Your ID:</b> <code>{user_id}</code>

📊 <b>Admin Statistics:</b>
• Total Users: {len(user_manager.get_all_users())}
• Active Users: {len(user_manager.get_active_users())}
• Messages: {len(custom_messages)}
• Sessions: {len(instagram_sessions)}
• Spam Status: {'🟢 Active' if spam_active else '🔴 Inactive'}

⚙️ <b>Admin Commands:</b>
• /users - View all users
• /addadmin [user_id] - Make user admin
• /removeadmin [user_id] - Remove admin
• /deleteuser [user_id] - Delete user
• /broadcast [message] - Broadcast to all users
• /addtime [user_id] [days] - Add time to user
• /cleanup - Clean old data
• /backup - Create backup
• /restore - Restore from backup
• /stats_all - Detailed statistics

🛠️ <b>Quick Actions:</b>
"""
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton(text="👥 View All Users", callback_data="admin_users"),
            InlineKeyboardButton(text="📊 Full Statistics", callback_data="admin_stats")
        )
        keyboard.add(
            InlineKeyboardButton(text="📢 Send Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton(text="⏰ Add User Time", callback_data="admin_addtime")
        )
        keyboard.add(
            InlineKeyboardButton(text="🗑️ Cleanup Data", callback_data="admin_cleanup"),
            InlineKeyboardButton(text="💾 Backup", callback_data="admin_backup")
        )
        keyboard.add(
            InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")
        )
        
        bot.send_message(message.chat.id, admin_text, reply_markup=keyboard)
    else:
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
        plan = data.get('plan', 'Free')
        active = "✅" if data.get('active', True) else "❌"
        joined = data.get('joined', 'Unknown').split('T')[0]
        
        response += f"<b>{is_admin}</b>\n"
        response += f"ID: <code>{uid}</code>\n"
        response += f"Name: {username}\n"
        response += f"Plan: {plan}\n"
        response += f"Active: {active}\n"
        response += f"Joined: {joined}\n"
        response += "─" * 20 + "\n\n"
    
    response += f"📊 <b>Total:</b> {len(users)} users"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="➕ Make Admin", callback_data="admin_make_admin"),
        InlineKeyboardButton(text="➖ Remove Admin", callback_data="admin_remove_admin")
    )
    keyboard.add(
        InlineKeyboardButton(text="🗑️ Delete User", callback_data="admin_delete_user_menu"),
        InlineKeyboardButton(text="⏰ Add Time", callback_data="admin_add_time_menu")
    )
    keyboard.add(
        InlineKeyboardButton(text="◀️ Back to Admin", callback_data="admin_panel")
    )
    
    bot.send_message(message.chat.id, response, reply_markup=keyboard)

@bot.message_handler(commands=['addadmin'])
def addadmin_command(message):
    """Make a user admin"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    try:
        # Extract user ID from command
        parts = message.text.split()
        if len(parts) < 2:
            bot.send_message(message.chat.id, "Usage: /addadmin [user_id]")
            return
        
        target_user_id = int(parts[1])
        
        if user_manager.set_admin(target_user_id, True):
            bot.send_message(message.chat.id, f"✅ User <code>{target_user_id}</code> is now admin!")
        else:
            bot.send_message(message.chat.id, f"❌ User <code>{target_user_id}</code> not found!")
    except:
        bot.send_message(message.chat.id, "❌ Invalid format! Use: /addadmin [user_id]")

@bot.message_handler(commands=['removeadmin'])
def removeadmin_command(message):
    """Remove admin from user"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.send_message(message.chat.id, "Usage: /removeadmin [user_id]")
            return
        
        target_user_id = int(parts[1])
        
        if target_user_id == ADMIN_USER_ID:
            bot.send_message(message.chat.id, "❌ Cannot remove primary admin!")
            return
        
        if user_manager.set_admin(target_user_id, False):
            bot.send_message(message.chat.id, f"✅ Admin rights removed from <code>{target_user_id}</code>")
        else:
            bot.send_message(message.chat.id, f"❌ User <code>{target_user_id}</code> not found!")
    except:
        bot.send_message(message.chat.id, "❌ Invalid format! Use: /removeadmin [user_id]")

@bot.message_handler(commands=['deleteuser'])
def deleteuser_command(message):
    """Delete a user"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.send_message(message.chat.id, "Usage: /deleteuser [user_id]")
            return
        
        target_user_id = int(parts[1])
        
        if target_user_id == ADMIN_USER_ID:
            bot.send_message(message.chat.id, "❌ Cannot delete primary admin!")
            return
        
        if user_manager.delete_user(target_user_id):
            bot.send_message(message.chat.id, f"✅ User <code>{target_user_id}</code> deleted!")
        else:
            bot.send_message(message.chat.id, f"❌ User <code>{target_user_id}</code> not found!")
    except:
        bot.send_message(message.chat.id, "❌ Invalid format! Use: /deleteuser [user_id]")

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    """Broadcast message to all users"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    try:
        # Extract message from command
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
        bot.send_message(message.chat.id, f"❌ Broadcast error: {str(e)}")

@bot.message_handler(commands=['addtime'])
def addtime_command(message):
    """Add time to user's subscription"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 3:
            bot.send_message(message.chat.id, "Usage: /addtime [user_id] [days]")
            return
        
        target_user_id = int(parts[1])
        days = int(parts[2])
        
        if user_manager.add_user_time(target_user_id, days):
            bot.send_message(message.chat.id, 
                f"✅ Added {days} days to user <code>{target_user_id}</code>\n\n"
                f"User now has access for {days} more days."
            )
        else:
            bot.send_message(message.chat.id, f"❌ User <code>{target_user_id}</code> not found!")
    except:
        bot.send_message(message.chat.id, "❌ Invalid format! Use: /addtime [user_id] [days]")

@bot.message_handler(commands=['cleanup'])
def cleanup_command(message):
    """Cleanup old data"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    bot.send_message(message.chat.id, "🧹 Cleaning up data...")
    
    # Count before cleanup
    total_users = len(user_manager.get_all_users())
    
    # Deactivate expired users
    expired_count = 0
    for uid, data in user_manager.users.items():
        if uid == str(ADMIN_USER_ID):
            continue  # Don't touch admin
        
        expiry_str = data.get('expiry', '')
        if expiry_str:
            try:
                expiry = datetime.fromisoformat(expiry_str)
                if datetime.now() > expiry:
                    data['active'] = False
                    expired_count += 1
            except:
                pass
    
    if expired_count > 0:
        user_manager.save_users()
    
    active_users = len(user_manager.get_active_users())
    
    bot.send_message(message.chat.id,
        f"✅ <b>Cleanup Complete!</b>\n\n"
        f"• Total Users: {total_users}\n"
        f"• Active Users: {active_users}\n"
        f"• Deactivated: {expired_count} expired users\n\n"
        f"<i>Expired users have been deactivated.</i>"
    )

@bot.message_handler(commands=['backup'])
def backup_command(message):
    """Create backup of data"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    try:
        # Create backup directory
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"backup_{timestamp}.json"
        
        # Collect all data
        backup_data = {
            "timestamp": datetime.now().isoformat(),
            "users": user_manager.users,
            "messages": custom_messages,
            "sessions": instagram_sessions,
            "settings": current_settings,
            "statistics": {
                "success_count": success_count,
                "unsuccess_count": unsuccess_count
            }
        }
        
        # Save backup
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        bot.send_message(message.chat.id,
            f"✅ <b>Backup Created!</b>\n\n"
            f"📁 File: <code>{backup_file.name}</code>\n"
            f"🕒 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"📊 Contents:\n"
            f"• Users: {len(user_manager.users)}\n"
            f"• Messages: {len(custom_messages)}\n"
            f"• Sessions: {len(instagram_sessions)}\n\n"
            f"<i>Backup saved in 'backups' folder.</i>"
        )
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Backup error: {str(e)}")

@bot.message_handler(commands=['stats_all'])
def stats_all_command(message):
    """Detailed statistics - Admin only"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_USER_ID:
        bot.send_message(message.chat.id, "❌ Admin only!")
        return
    
    total_users = len(user_manager.get_all_users())
    active_users = len(user_manager.get_active_users())
    admin_users = sum(1 for u in user_manager.users.values() if u.get('is_admin'))
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    stats_text = f"""
📊 <b>DETAILED STATISTICS</b>

👥 <b>USER STATISTICS:</b>
• Total Users: {total_users}
• Active Users: {active_users}
• Admin Users: {admin_users}
• Inactive Users: {total_users - active_users}

💬 <b>MESSAGE STATISTICS:</b>
• Saved Messages: {len(custom_messages)}
• Sent Successfully: {success_count}
• Failed to Send: {unsuccess_count}
• Success Rate: {(success_count/(success_count+unsuccess_count)*100 if (success_count+unsuccess_count) > 0 else 0):.1f}%

🔑 <b>SESSION STATISTICS:</b>
• Total Sessions: {len(instagram_sessions)}
• Valid Sessions: {valid_sessions}
• Invalid Sessions: {len(instagram_sessions) - valid_sessions}

⚙️ <b>SETTINGS:</b>
• Target: {current_settings['target'] or 'Not set'}
• Delay: {current_settings['delay_min']}-{current_settings['delay_max']}s
• Message Count: {current_settings['message_count']}
• Spam Active: {'🟢 Yes' if spam_active else '🔴 No'}

💾 <b>DATA INFO:</b>
• Users File: {Path('users_data.json').stat().st_size if Path('users_data.json').exists() else 0} bytes
• Messages File: {MESSAGES_FILE.stat().st_size if MESSAGES_FILE.exists() else 0} bytes
• Sessions File: {SESSIONS_FILE.stat().st_size if SESSIONS_FILE.exists() else 0} bytes

🕒 <b>LAST UPDATE:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    bot.send_message(message.chat.id, stats_text)

# ========== BASIC BOT COMMANDS ==========
@bot.message_handler(commands=['addmsg'])
def addmsg_command(message):
    """Add message for spamming"""
    msg = bot.send_message(message.chat.id, 
        "✍️ <b>Send the message you want to spam:</b>\n\n"
        "Use <code>{target}</code> as a placeholder for target username.\n\n"
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

@bot.message_handler(commands=['listmsg'])
def listmsg_command(message):
    """List all saved messages"""
    if not custom_messages:
        bot.send_message(message.chat.id, "📭 No messages saved!")
        return
    
    response = "📋 <b>SAVED MESSAGES:</b>\n\n"
    
    for i, msg in enumerate(custom_messages, 1):
        preview = msg[:60] + "..." if len(msg) > 60 else msg
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
            f"✅ <b>Session Added!</b>\n\n"
            f"👤 <b>Username:</b> {username}\n"
            f"🕒 <b>Added:</b> {datetime.now().strftime('%H:%M:%S')}\n"
            f"📊 <b>Valid Sessions:</b> {len([s for s in instagram_sessions if s.get('status') == 'valid'])}"
        )
    else:
        bot.send_message(message.chat.id, f"❌ <b>Invalid Session!</b>\n\n{info}")

@bot.message_handler(commands=['sessions'])
def sessions_command(message):
    """View Instagram sessions"""
    if not instagram_sessions:
        bot.send_message(message.chat.id, "🔐 No Instagram sessions!")
        return
    
    valid_sessions = [s for s in instagram_sessions if s.get('status') == 'valid']
    
    response = "👥 <b>INSTAGRAM SESSIONS</b>\n\n"
    
    if valid_sessions:
        response += "✅ <b>VALID:</b>\n"
        for i, session in enumerate(valid_sessions, 1):
            username = session.get('username', 'Unknown')
            added = session.get('added', 'Unknown')
            response += f"{i}. <b>{username}</b> - {added}\n"
    
    invalid_sessions = [s for s in instagram_sessions if s.get('status') != 'valid']
    if invalid_sessions:
        response += "\n❌ <b>INVALID:</b>\n"
        for i, session in enumerate(invalid_sessions, 1):
            username = session.get('username', 'Unknown')
            response += f"{i}. {username}\n"
    
    response += f"\n📊 {len(valid_sessions)} valid, {len(invalid_sessions)} invalid"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton(text="➕ Add Session", callback_data="add_session"),
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

🎯 <b>Target:</b> {current_settings['target'] or 'Not set'}
🔗 <b>URL:</b> {'✅ Set' if current_settings['dm_url'] else '❌ Not set'}
⏱️ <b>Delay:</b> {current_settings['delay_min']}-{current_settings['delay_max']}s
📊 <b>Count:</b> {current_settings['message_count']}
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
    
    bot.send_message(message.chat.id, current_config + "\n<b>Select option:</b>", reply_markup=keyboard)

@bot.message_handler(commands=['start_spam'])
def start_spam_command(message):
    """Start spam"""
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
        bot.send_message(message.chat.id, "❌ Invalid URL! Couldn't get thread ID")
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
        f"✅ <b>SPAM STARTED!</b>\n\n"
        f"🎯 <b>Target:</b> {current_settings['target']}\n"
        f"🔗 <b>Thread:</b> {thread_id[:30]}...\n"
        f"📊 <b>Messages:</b> {len(custom_messages)}\n"
        f"👥 <b>Accounts:</b> {valid_sessions}\n"
        f"⏱️ <b>Delay:</b> {current_settings['delay_min']}-{current_settings['delay_max']}s\n"
        f"📝 <b>Count:</b> {current_settings['message_count']}"
    )

def spam_worker(chat_id, thread_id):
    """Spam worker"""
    global spam_active, success_count, unsuccess_count
    
    available_sessions = instagram_sessions
    
    if not available_sessions:
        bot.send_message(chat_id, "❌ No sessions!")
        spam_active = False
        return
    
    counter = 0
    session_index = 0
    
    while spam_active and counter < current_settings['message_count']:
        try:
            # Get message
            msg = random.choice(custom_messages)
            formatted_msg = msg.replace("{target}", current_settings['target'])
            
            # Get session
            session = available_sessions[session_index % len(available_sessions)]
            session_id = session.get('session_id')
            username = session.get('username', 'Account')
            
            # Send message
            success, result = send_instagram_message(session_id, thread_id, formatted_msg)
            
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
            if counter % 10 == 0:
                total = success_count + unsuccess_count
                rate = (success_count/total*100) if total > 0 else 0
                bot.send_message(chat_id,
                    f"📊 Progress: {counter}/{current_settings['message_count']}\n"
                    f"✅ {success_count} | ❌ {unsuccess_count}\n"
                    f"📈 {rate:.1f}% success",
                    disable_notification=True
                )
            
            session_index += 1
            
            # Delay
            delay = random.uniform(current_settings['delay_min'], current_settings['delay_max'])
            time.sleep(delay)
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)
    
    # Done
    spam_active = False
    
    total = success_count + unsuccess_count
    rate = (success_count/total*100) if total > 0 else 0
    
    bot.send_message(chat_id, f"""
✅ SPAM COMPLETE!

📊 Final:
• Sent: {counter}
• ✅ Success: {success_count}
• ❌ Failed: {unsuccess_count}
• 📈 Rate: {rate:.1f}%
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
    """Show stats"""
    total = success_count + unsuccess_count
    rate = (success_count/total*100) if total > 0 else 0
    valid_sessions = len([s for s in instagram_sessions if s.get('status') == 'valid'])
    
    stats_text = f"""
📊 <b>STATISTICS</b>

✅ <b>Success:</b> {success_count}
❌ <b>Failed:</b> {unsuccess_count}
📈 <b>Rate:</b> {rate:.1f}%

💬 <b>Messages:</b> {len(custom_messages)}
👥 <b>Sessions:</b> {valid_sessions} valid

🎯 <b>Target:</b> {current_settings['target'] or 'None'}
🔗 <b>URL:</b> {'✅' if current_settings['dm_url'] else '❌'}

⏱️ <b>Delay:</b> {current_settings['delay_min']}-{current_settings['delay_max']}s
📝 <b>Count:</b> {current_settings['message_count']}

🔴 <b>Status:</b> {'🟢 ACTIVE' if spam_active else '🔴 INACTIVE'}
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
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    """Handle all callback queries"""
    if call.data == "main_menu":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        send_start_message(call.message.chat.id)
    
    elif call.data == "admin_panel":
        admin_command(call.message)
    
    elif call.data == "admin_users":
        users_command(call.message)
    
    elif call.data == "admin_stats":
        stats_all_command(call.message)
    
    elif call.data in ["admin_broadcast", "admin_addtime", "admin_cleanup", "admin_backup"]:
        bot.answer_callback_query(call.id, "Use the command: /" + call.data.split('_')[1])
    
    elif call.data == "add_msg":
        msg = bot.send_message(call.message.chat.id, "✍️ Send message:")
        bot.register_next_step_handler(msg, process_new_message)
        bot.answer_callback_query(call.id)
    
    elif call.data == "list_msg":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        listmsg_command(call.message)
    
    elif call.data == "add_session":
        msg = bot.send_message(call.message.chat.id, "🔑 Send session ID:")
        bot.register_next_step_handler(msg, process_new_session)
        bot.answer_callback_query(call.id)
    
    elif call.data == "list_sessions":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        sessions_command(call.message)
    
    elif call.data == "setup":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        setup_command(call.message)
    
    elif call.data == "start_spam":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        start_spam_command(call.message)
    
    elif call.data == "stop_spam":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        stop_spam_command(call.message)
    
    elif call.data == "stats":
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        stats_command(call.message)
    
    elif call.data == "set_target":
        msg = bot.send_message(call.message.chat.id, "🎯 Send target username:")
        bot.register_next_step_handler(msg, process_target)
        bot.answer_callback_query(call.id)
    
    elif call.data == "set_url":
        msg = bot.send_message(call.message.chat.id, "🔗 Send Instagram URL:")
        bot.register_next_step_handler(msg, process_url)
        bot.answer_callback_query(call.id)
    
    elif call.data == "set_count":
        msg = bot.send_message(call.message.chat.id, "📊 Send message count:")
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
        bot.send_message(call.message.chat.id, "⏱️ Select delay:", reply_markup=keyboard)
        bot.answer_callback_query(call.id)
    
    elif call.data.startswith("delay_"):
        delays = call.data.split("_")[1:]
        current_settings['delay_min'] = float(delays[0])
        current_settings['delay_max'] = float(delays[1])
        bot.send_message(call.message.chat.id, f"✅ Delay: {delays[0]}-{delays[1]}s")
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
        
        bot.edit_message_text("🗑️ Delete:", call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    
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
        
        bot.edit_message_text("🗑️ Delete:", call.message.chat.id, call.message.message_id, reply_markup=keyboard)
    
    elif call.data.startswith("del_sess_"):
        try:
            index = int(call.data.split("_")[2])
            instagram_sessions.pop(index)
            save_sessions()
            bot.answer_callback_query(call.id, "✅ Deleted!")
            sessions_command(call.message)
        except:
            bot.answer_callback_query(call.id, "❌ Error!")

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
        bot.send_message(message.chat.id, "⚠️ URL saved (thread ID not detected)")

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

# ========== MAIN ==========
if __name__ == "__main__":
    print(print_banner())
    print(f"🤖 Instagram Spam Bot v7.0 - COMPLETE")
    print(f"👑 Admin User ID: {ADMIN_USER_ID}")
    print(f"💬 Messages: {len(custom_messages)}")
    print(f"🔑 Sessions: {len(instagram_sessions)}")
    
    try:
        bot_info = bot.get_me()
        print(f"✅ Bot: @{bot_info.username}")
        print(f"✅ Bot ID: {bot_info.id}")
        print("✅ Ready! Send /start")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        sys.exit(1)
    
    print("\n🚀 Starting bot...")
    bot.infinity_polling()
