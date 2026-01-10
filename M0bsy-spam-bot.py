#!/usr/bin/env python3
"""
COMPLETE INSTAGRAM SPAM BOT - FULLY WORKING VERSION
Author: M0bsy
GitHub: https://github.com/M0bsyy/M0bsy-spam-bot.git
ADMIN: 6107382622
"""

import os
import sys
import json
import random
import time
import threading
import requests
import hashlib
import logging
import traceback
import asyncio
import re
import datetime
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
from queue import Queue

import telebot
from telebot import types, apihelper
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery

# ========== LOGGING SETUP ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_debug.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# ========== CONFIGURATION ==========
BOT_TOKEN = "8595686704:AAGZ6-f7cjiaET1J2yXM-QBuJCq_fyOMJ7o"  # Your bot token
ADMIN_IDS = [6107382622]  # Your user ID - MAKE SURE THIS IS CORRECT
BOT_USERNAME = "@M0bsy_spam_bot"
CONTACT_USER = "@M0bsy_olds"

# ========== INITIALIZE BOT ==========
try:
    bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")
    logger.info("Bot initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize bot: {e}")
    sys.exit(1)

# ========== DATA STORAGE ==========
class DataStorage:
    """Handles all data storage operations"""
    
    def __init__(self):
        self.data_dir = Path("bot_data")
        self.data_dir.mkdir(exist_ok=True)
        
        self.files = {
            'users': self.data_dir / 'users.json',
            'sessions': self.data_dir / 'sessions.json',
            'messages': self.data_dir / 'messages.json',
            'settings': self.data_dir / 'settings.json',
            'stats': self.data_dir / 'stats.json'
        }
        
        # Initialize data
        self.users = self.load_file('users', {})
        self.sessions = self.load_file('sessions', [])
        self.messages = self.load_file('messages', [])
        self.settings = self.load_file('settings', self.get_default_settings())
        self.stats = self.load_file('stats', self.get_default_stats())
        
        # Initialize admin user
        self.initialize_admin()
        
        logger.info(f"Data loaded: {len(self.users)} users, {len(self.sessions)} sessions, {len(self.messages)} messages")
    
    def get_default_settings(self):
        return {
            "target": "instagram_user",
            "delay_min": 2,
            "delay_max": 5,
            "dm_url": "",
            "thread_id": "",
            "continuous_mode": True,
            "messages_sent": 0,
            "spam_active": False,
            "last_target": "",
            "max_sessions_per_user": 5
        }
    
    def get_default_stats(self):
        return {
            "total_messages_sent": 0,
            "successful_messages": 0,
            "failed_messages": 0,
            "bot_start_time": datetime.now().isoformat(),
            "total_users": 0,
            "active_sessions": 0
        }
    
    def load_file(self, file_key, default):
        """Load data from JSON file"""
        file_path = self.files[file_key]
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {file_key}: {e}")
        return default
    
    def save_file(self, file_key, data):
        """Save data to JSON file"""
        file_path = self.files[file_key]
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error saving {file_key}: {e}")
            return False
    
    def save_all(self):
        """Save all data"""
        self.save_file('users', self.users)
        self.save_file('sessions', self.sessions)
        self.save_file('messages', self.messages)
        self.save_file('settings', self.settings)
        self.save_file('stats', self.stats)
        logger.debug("All data saved")
    
    def initialize_admin(self):
        """Initialize admin user"""
        for admin_id in ADMIN_IDS:
            admin_id_str = str(admin_id)
            if admin_id_str not in self.users:
                self.users[admin_id_str] = {
                    "id": admin_id,
                    "username": "ADMIN",
                    "is_admin": True,
                    "plan": "lifetime_admin",
                    "expiry": (datetime.now() + timedelta(days=36500)).isoformat(),
                    "joined": datetime.now().isoformat(),
                    "active": True,
                    "message_count": 0,
                    "last_seen": datetime.now().isoformat()
                }
                logger.info(f"Admin user initialized: {admin_id}")
        self.save_file('users', self.users)
    
    def add_user(self, user_id, username=""):
        """Add or update user"""
        user_id_str = str(user_id)
        is_admin = user_id in ADMIN_IDS
        
        if user_id_str not in self.users:
            # New user
            if is_admin:
                expiry = datetime.now() + timedelta(days=36500)
                plan = "lifetime_admin"
            else:
                expiry = datetime.now() + timedelta(hours=1)
                plan = "1_hour_trial"
            
            self.users[user_id_str] = {
                "id": user_id,
                "username": username or f"User_{user_id}",
                "is_admin": is_admin,
                "plan": plan,
                "expiry": expiry.isoformat(),
                "joined": datetime.now().isoformat(),
                "active": True,
                "message_count": 0,
                "last_seen": datetime.now().isoformat()
            }
            logger.info(f"New user added: {user_id} ({username})")
        else:
            # Update existing user
            self.users[user_id_str]["username"] = username or self.users[user_id_str].get("username", "")
            self.users[user_id_str]["last_seen"] = datetime.now().isoformat()
        
        self.save_file('users', self.users)
        return self.users[user_id_str]
    
    def get_user(self, user_id):
        """Get user by ID"""
        user_id_str = str(user_id)
        return self.users.get(user_id_str)
    
    def is_admin(self, user_id):
        """Check if user is admin"""
        if user_id in ADMIN_IDS:
            return True
        
        user = self.get_user(user_id)
        if user:
            return user.get("is_admin", False)
        return False
    
    def check_user_access(self, user_id):
        """Check if user has access"""
        if user_id in ADMIN_IDS:
            return True, "✅ Admin access"
        
        user = self.get_user(user_id)
        if not user:
            return False, "❌ User not registered. Use /start to register."
        
        if not user.get("active", True):
            return False, "❌ Account deactivated"
        
        expiry_str = user.get("expiry")
        if expiry_str:
            try:
                expiry = datetime.fromisoformat(expiry_str)
                if datetime.now() > expiry:
                    user["active"] = False
                    self.save_file('users', self.users)
                    return False, "❌ Trial expired. Contact admin for access."
            except:
                pass
        
        return True, "✅ Access granted"
    
    def add_message(self, text, author_id):
        """Add spam message"""
        message_id = hashlib.md5(f"{text}{author_id}{time.time()}".encode()).hexdigest()[:8]
        message = {
            "id": message_id,
            "text": text,
            "author_id": author_id,
            "created": datetime.now().isoformat(),
            "used_count": 0
        }
        self.messages.append(message)
        self.save_file('messages', self.messages)
        return message
    
    def add_session(self, session_id, username="", status="pending"):
        """Add Instagram session"""
        session = {
            "session_id": session_id,
            "username": username,
            "status": status,
            "added": datetime.now().isoformat(),
            "last_used": datetime.now().isoformat(),
            "message_count": 0,
            "success_count": 0,
            "fail_count": 0
        }
        self.sessions.append(session)
        self.save_file('sessions', self.sessions)
        return session
    
    def update_session(self, session_id, updates):
        """Update session data"""
        for session in self.sessions:
            if session.get("session_id") == session_id:
                session.update(updates)
                session["last_used"] = datetime.now().isoformat()
                self.save_file('sessions', self.sessions)
                return True
        return False
    
    def get_valid_sessions(self):
        """Get valid sessions"""
        return [s for s in self.sessions if s.get("status") == "valid"]

# ========== GLOBAL DATA ==========
storage = DataStorage()

# ========== SPAM CONTROL ==========
spam_active = False
spam_thread = None
success_count = 0
fail_count = 0
total_sent = 0
spam_lock = threading.Lock()

# ========== UTILITY FUNCTIONS ==========
def extract_thread_id(url):
    """Extract thread ID from Instagram URL"""
    try:
        url = url.strip()
        
        # If numeric, return as is
        if url.isdigit() and len(url) > 8:
            return url
        
        # Extract from various formats
        patterns = [
            r'/direct/t/([0-9]+)',
            r'thread_id=([0-9]+)',
            r't/([0-9]+)',
            r'([0-9]{15,})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    except Exception as e:
        logger.error(f"Error extracting thread ID: {e}")
        return None

def validate_instagram_session(session_id):
    """Validate Instagram session"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        # Try to get user info
        response = requests.get(
            'https://www.instagram.com/api/v1/users/web_profile_info/?username=instagram',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('status') == 'ok':
                    username = "instagram_user"
                    if 'data' in data and 'user' in data['data']:
                        username = data['data']['user'].get('username', 'instagram_user')
                    return True, username, "✅ Valid session"
            except:
                pass
        
        # Alternative check
        response = requests.get(
            'https://www.instagram.com/accounts/edit/',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            if 'instagram' in response.text.lower():
                # Extract username
                username = "instagram_user"
                match = re.search(r'"username":"([^"]+)"', response.text)
                if match:
                    username = match.group(1)
                return True, username, "✅ Valid session"
        
        return False, "", "❌ Invalid session ID"
        
    except requests.exceptions.Timeout:
        return False, "", "❌ Connection timeout"
    except requests.exceptions.ConnectionError:
        return False, "", "❌ Connection error"
    except Exception as e:
        return False, "", f"❌ Error: {str(e)}"

def send_instagram_dm(session_id, thread_id, message):
    """Send Instagram Direct Message"""
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
            match = re.search(r'"csrf_token":"([^"]+)"', response.text)
            if match:
                csrf_token = match.group(1)
        
        if not csrf_token:
            csrf_token = "missing"
        
        # Prepare headers
        headers = {
            'authority': 'www.instagram.com',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'cookie': f'sessionid={session_id}; csrftoken={csrf_token}',
            'origin': 'https://www.instagram.com',
            'referer': 'https://www.instagram.com/direct/inbox/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'x-csrftoken': csrf_token,
            'x-ig-app-id': '936619743392459',
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
            return False, f"❌ HTTP {response.status_code}"
            
    except Exception as e:
        return False, f"❌ Error: {str(e)}"

# ========== SPAM WORKER ==========
def spam_worker(chat_id, thread_id, user_id):
    """Main spam worker function"""
    global spam_active, success_count, fail_count, total_sent
    
    logger.info(f"Spam worker started for user {user_id}")
    
    try:
        settings = storage.settings
        target = settings.get("target", "user")
        delay_min = settings.get("delay_min", 2)
        delay_max = settings.get("delay_max", 5)
        
        valid_sessions = storage.get_valid_sessions()
        messages = storage.messages
        
        if not valid_sessions:
            bot.send_message(chat_id, "❌ No valid sessions!")
            spam_active = False
            return
        
        if not messages:
            bot.send_message(chat_id, "❌ No messages!")
            spam_active = False
            return
        
        # Send starting message
        start_msg = bot.send_message(
            chat_id,
            f"🚀 <b>SPAM STARTED!</b>\n\n"
            f"🎯 Target: {target}\n"
            f"🔗 Thread ID: {thread_id}\n"
            f"📝 Messages: {len(messages)}\n"
            f"👥 Sessions: {len(valid_sessions)}\n\n"
            f"<i>Starting spam process...</i>"
        )
        
        session_index = 0
        message_counter = 0
        
        while spam_active:
            try:
                # Check user access
                if message_counter % 10 == 0:
                    has_access, _ = storage.check_user_access(user_id)
                    if not has_access:
                        bot.send_message(chat_id, "❌ Access terminated!")
                        spam_active = False
                        break
                
                # Get random message
                if not messages:
                    break
                
                msg_data = random.choice(messages)
                message_text = msg_data.get("text", "")
                formatted_msg = message_text.replace("{target}", target)
                
                # Get session
                session = valid_sessions[session_index % len(valid_sessions)]
                session_id = session.get("session_id")
                
                # Send message
                success, result = send_instagram_dm(session_id, thread_id, formatted_msg)
                
                with spam_lock:
                    total_sent += 1
                    message_counter += 1
                    storage.settings["messages_sent"] = total_sent
                    
                    if success:
                        success_count += 1
                        session["success_count"] = session.get("success_count", 0) + 1
                    else:
                        fail_count += 1
                        session["fail_count"] = session.get("fail_count", 0) + 1
                    
                    session["message_count"] = session.get("message_count", 0) + 1
                    session["last_used"] = datetime.now().isoformat()
                
                storage.save_file('sessions', storage.sessions)
                storage.save_file('settings', storage.settings)
                
                # Update message usage
                msg_data["used_count"] = msg_data.get("used_count", 0) + 1
                storage.save_file('messages', storage.messages)
                
                # Next session
                session_index += 1
                
                # Send update every 10 messages
                if message_counter % 10 == 0:
                    total = success_count + fail_count
                    success_rate = (success_count / total * 100) if total > 0 else 0
                    
                    try:
                        bot.edit_message_text(
                            f"📊 <b>SPAM PROGRESS</b>\n\n"
                            f"✅ Sent: {message_counter}\n"
                            f"✅ Success: {success_count}\n"
                            f"❌ Failed: {fail_count}\n"
                            f"📈 Rate: {success_rate:.1f}%\n\n"
                            f"<i>Running... Use /stop_spam to stop</i>",
                            chat_id=chat_id,
                            message_id=start_msg.message_id
                        )
                    except:
                        pass
                
                # Random delay
                delay = random.uniform(delay_min, delay_max)
                time.sleep(delay)
                
            except Exception as e:
                logger.error(f"Error in spam loop: {e}")
                time.sleep(5)
                
    except Exception as e:
        logger.error(f"Critical spam error: {e}")
        bot.send_message(chat_id, f"❌ Spam error: {str(e)}")
    finally:
        spam_active = False
        
        # Final report
        total = success_count + fail_count
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        bot.send_message(
            chat_id,
            f"🛑 <b>SPAM STOPPED</b>\n\n"
            f"📊 Final Stats:\n"
            f"✅ Successful: {success_count}\n"
            f"❌ Failed: {fail_count}\n"
            f"📈 Success Rate: {success_rate:.1f}%\n"
            f"📤 Total Sent: {message_counter}"
        )

# ========== COMMAND HANDLERS ==========
@bot.message_handler(commands=['start'])
def start_command(message):
    """Handle /start command"""
    try:
        user_id = message.from_user.id
        username = message.from_user.username or message.from_user.first_name or "User"
        
        logger.info(f"/start from {user_id} ({username})")
        
        # Add/update user
        storage.add_user(user_id, username)
        
        # Check if admin
        is_admin = storage.is_admin(user_id)
        
        # Get stats
        valid_sessions = len(storage.get_valid_sessions())
        total_messages = len(storage.messages)
        total_sent = storage.settings.get("messages_sent", 0)
        
        welcome_text = f"""
🤖 <b>INSTAGRAM SPAM BOT</b>

👤 <b>User:</b> {username}
🆔 <b>ID:</b> <code>{user_id}</code>
{'🛡️ <b>Status:</b> ✅ ADMIN' if is_admin else '👤 <b>Status:</b> Trial User'}

📊 <b>System Status:</b>
• Messages: {total_messages}
• Valid Sessions: {valid_sessions}
• Total Sent: {total_sent}
• Spam: {'🟢 RUNNING' if spam_active else '🔴 STOPPED'}

📋 <b>Available Commands:</b>
• /addmsg - Add spam message
• /listmsg - List messages
• /addsession - Add Instagram session
• /sessions - View sessions
• /setup - Configure spam
• /start_spam - Start spam
• /stop_spam - Stop spam
• /stats - View statistics
{'• /admin - Admin panel' if is_admin else ''}

💡 <b>Tips:</b>
• Use {target} in messages for target username
• Add multiple sessions for better results
• Set proper delays to avoid bans
"""
        
        # Create keyboard
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        keyboard.add(
            InlineKeyboardButton("➕ Add Message", callback_data="add_msg"),
            InlineKeyboardButton("🔑 Add Session", callback_data="add_session"),
            InlineKeyboardButton("📋 Messages", callback_data="list_msg"),
            InlineKeyboardButton("👥 Sessions", callback_data="list_sessions"),
            InlineKeyboardButton("⚙️ Setup", callback_data="setup"),
            InlineKeyboardButton("🚀 Start Spam", callback_data="start_spam"),
            InlineKeyboardButton("🛑 Stop Spam", callback_data="stop_spam"),
            InlineKeyboardButton("📊 Stats", callback_data="stats")
        )
        
        if is_admin:
            keyboard.add(
                InlineKeyboardButton("🔐 ADMIN PANEL", callback_data="admin_panel"),
                InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")
            )
        
        bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['admin'])
def admin_command(message):
    """Admin panel"""
    try:
        user_id = message.from_user.id
        
        if not storage.is_admin(user_id):
            bot.send_message(
                message.chat.id,
                "❌ <b>ACCESS DENIED!</b>\n\n"
                "This command is for administrators only."
            )
            return
        
        logger.info(f"Admin panel accessed by {user_id}")
        
        # Get stats
        total_users = len(storage.users)
        valid_sessions = len(storage.get_valid_sessions())
        total_messages = len(storage.messages)
        
        admin_text = f"""
🔐 <b>ADMIN PANEL</b>

🛡️ <b>Welcome, Admin!</b>
🆔 <b>Your ID:</b> <code>{user_id}</code>

📊 <b>System Overview:</b>
• Total Users: {total_users}
• Valid Sessions: {valid_sessions}
• Total Messages: {total_messages}
• Messages Sent: {storage.settings.get('messages_sent', 0)}
• Spam Active: {'🟢 YES' if spam_active else '🔴 NO'}

⚙️ <b>Admin Commands:</b>
• /users - View all users
• /broadcast - Send message to all users
• /addtime - Add time to user
• /backup - Create backup
"""
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        keyboard.add(
            InlineKeyboardButton("👥 View Users", callback_data="admin_users"),
            InlineKeyboardButton("📊 System Stats", callback_data="admin_stats"),
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("⏰ Add Time", callback_data="admin_addtime"),
            InlineKeyboardButton("💾 Backup", callback_data="admin_backup"),
            InlineKeyboardButton("🔄 Refresh", callback_data="admin_refresh"),
            InlineKeyboardButton("◀️ Main Menu", callback_data="main_menu")
        )
        
        bot.send_message(message.chat.id, admin_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in admin_command: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['addmsg'])
def addmsg_command(message):
    """Add spam message"""
    try:
        user_id = message.from_user.id
        
        has_access, msg = storage.check_user_access(user_id)
        if not has_access:
            bot.send_message(message.chat.id, msg)
            return
        
        bot.send_message(
            message.chat.id,
            "✍️ <b>Send your spam message:</b>\n\n"
            "Use <code>{target}</code> to insert target username\n"
            "Example: Hello {target}! 👋"
        )
        
        bot.register_next_step_handler(message, process_add_message)
        
    except Exception as e:
        logger.error(f"Error in addmsg_command: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

def process_add_message(message):
    """Process new message"""
    try:
        user_id = message.from_user.id
        
        text = message.text.strip()
        if not text:
            bot.send_message(message.chat.id, "❌ Message cannot be empty!")
            return
        
        if len(text) > 1000:
            bot.send_message(message.chat.id, "❌ Message too long! Max 1000 characters.")
            return
        
        # Add message
        msg_data = storage.add_message(text, user_id)
        
        bot.send_message(
            message.chat.id,
            f"✅ <b>Message added!</b>\n\n"
            f"Preview: {text[:100]}...\n"
            f"ID: <code>{msg_data.get('id')}</code>\n"
            f"Total messages: {len(storage.messages)}"
        )
        
    except Exception as e:
        logger.error(f"Error in process_add_message: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['listmsg'])
def listmsg_command(message):
    """List all spam messages"""
    try:
        user_id = message.from_user.id
        
        has_access, msg = storage.check_user_access(user_id)
        if not has_access:
            bot.send_message(message.chat.id, msg)
            return
        
        messages = storage.messages
        
        if not messages:
            bot.send_message(message.chat.id, "📭 No messages found!")
            return
        
        response = "📋 <b>AVAILABLE MESSAGES:</b>\n\n"
        
        for i, msg in enumerate(messages[:20], 1):  # Show first 20
            preview = msg.get("text", "")[:50] + "..." if len(msg.get("text", "")) > 50 else msg.get("text", "")
            response += f"{i}. <code>{preview}</code>\n\n"
        
        response += f"📊 Total: {len(messages)} messages"
        
        bot.send_message(message.chat.id, response)
        
    except Exception as e:
        logger.error(f"Error in listmsg_command: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['addsession'])
def addsession_command(message):
    """Add Instagram session"""
    try:
        user_id = message.from_user.id
        
        has_access, msg = storage.check_user_access(user_id)
        if not has_access:
            bot.send_message(message.chat.id, msg)
            return
        
        instruction = """
🔑 <b>HOW TO GET INSTAGRAM SESSION ID:</b>

1. Open Instagram in Chrome
2. Login to your account
3. Press F12 for Developer Tools
4. Go to Application tab
5. Click Cookies → https://www.instagram.com
6. Find sessionid cookie
7. Copy the Value

📝 <b>Send the sessionid value:</b>
"""
        
        bot.send_message(message.chat.id, instruction)
        bot.register_next_step_handler(message, process_add_session)
        
    except Exception as e:
        logger.error(f"Error in addsession_command: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

def process_add_session(message):
    """Process new session"""
    try:
        user_id = message.from_user.id
        
        session_id = message.text.strip()
        if len(session_id) < 20:
            bot.send_message(message.chat.id, "❌ Invalid session ID!")
            return
        
        bot.send_message(message.chat.id, "🔍 Validating session...")
        
        valid, username, info = validate_instagram_session(session_id)
        
        if valid:
            # Add session
            session = storage.add_session(session_id, username, "valid")
            valid_sessions = len(storage.get_valid_sessions())
            
            bot.send_message(
                message.chat.id,
                f"✅ <b>SESSION ADDED!</b>\n\n"
                f"👤 Username: {username}\n"
                f"✅ Status: Valid\n"
                f"📊 Valid sessions: {valid_sessions}"
            )
        else:
            bot.send_message(
                message.chat.id,
                f"❌ <b>VALIDATION FAILED!</b>\n\n"
                f"Reason: {info}"
            )
        
    except Exception as e:
        logger.error(f"Error in process_add_session: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['sessions'])
def sessions_command(message):
    """View all Instagram sessions"""
    try:
        user_id = message.from_user.id
        
        has_access, msg = storage.check_user_access(user_id)
        if not has_access:
            bot.send_message(message.chat.id, msg)
            return
        
        sessions = storage.sessions
        valid_sessions = storage.get_valid_sessions()
        
        if not sessions:
            bot.send_message(message.chat.id, "🔐 No sessions found!")
            return
        
        response = f"""
👥 <b>INSTAGRAM SESSIONS</b>

✅ Valid: {len(valid_sessions)}
❌ Invalid: {len(sessions) - len(valid_sessions)}
📊 Total: {len(sessions)}
"""
        
        if valid_sessions:
            response += "\n✅ <b>VALID SESSIONS:</b>\n"
            for i, session in enumerate(valid_sessions[:10], 1):
                username = session.get("username", "Unknown")
                msg_count = session.get("message_count", 0)
                response += f"{i}. {username} - {msg_count} messages\n"
        
        bot.send_message(message.chat.id, response)
        
    except Exception as e:
        logger.error(f"Error in sessions_command: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['setup'])
def setup_command(message):
    """Setup spam configuration"""
    try:
        user_id = message.from_user.id
        
        has_access, msg = storage.check_user_access(user_id)
        if not has_access:
            bot.send_message(message.chat.id, msg)
            return
        
        settings = storage.settings
        
        config_text = f"""
⚙️ <b>SPAM CONFIGURATION</b>

🎯 Target: {settings.get('target', 'Not set')}
🔗 URL: {'✅ Set' if settings.get('dm_url') else '❌ Not set'}
⏱️ Delay: {settings.get('delay_min', 2)}-{settings.get('delay_max', 5)}s
♾️ Mode: {'CONTINUOUS' if settings.get('continuous_mode', True) else 'LIMITED'}
📊 Sent: {settings.get('messages_sent', 0)}
"""
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        keyboard.add(
            InlineKeyboardButton("🎯 Set Target", callback_data="set_target"),
            InlineKeyboardButton("🔗 Set URL", callback_data="set_url"),
            InlineKeyboardButton("⏱️ Set Delay", callback_data="set_delay"),
            InlineKeyboardButton("◀️ Back", callback_data="main_menu")
        )
        
        bot.send_message(message.chat.id, config_text, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Error in setup_command: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['start_spam'])
def start_spam_command(message):
    """Start continuous spam"""
    try:
        user_id = message.from_user.id
        
        has_access, msg = storage.check_user_access(user_id)
        if not has_access:
            bot.send_message(message.chat.id, msg)
            return
        
        global spam_active, spam_thread
        
        if spam_active:
            bot.send_message(message.chat.id, "⚠️ Spam is already running!")
            return
        
        # Check requirements
        if not storage.messages:
            bot.send_message(message.chat.id, "❌ No messages! Use /addmsg")
            return
        
        valid_sessions = storage.get_valid_sessions()
        if not valid_sessions:
            bot.send_message(message.chat.id, "❌ No valid sessions! Use /addsession")
            return
        
        dm_url = storage.settings.get('dm_url', '')
        if not dm_url:
            bot.send_message(message.chat.id, "❌ No URL set! Use /setup")
            return
        
        thread_id = extract_thread_id(dm_url)
        if not thread_id:
            bot.send_message(message.chat.id, "❌ Invalid URL format!")
            return
        
        # Start spam
        spam_active = True
        spam_thread = threading.Thread(
            target=spam_worker,
            args=(message.chat.id, thread_id, user_id),
            daemon=True
        )
        spam_thread.start()
        
        bot.send_message(
            message.chat.id,
            f"🚀 <b>SPAM STARTED!</b>\n\n"
            f"Thread ID: {thread_id}\n"
            f"Messages: {len(storage.messages)}\n"
            f"Sessions: {len(valid_sessions)}\n\n"
            f"<i>Use /stop_spam to stop</i>"
        )
        
    except Exception as e:
        logger.error(f"Error in start_spam_command: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['stop_spam'])
def stop_spam_command(message):
    """Stop spam"""
    try:
        user_id = message.from_user.id
        
        has_access, msg = storage.check_user_access(user_id)
        if not has_access:
            bot.send_message(message.chat.id, msg)
            return
        
        global spam_active
        
        if not spam_active:
            bot.send_message(message.chat.id, "⚠️ No spam is running!")
            return
        
        spam_active = False
        bot.send_message(message.chat.id, "🛑 Stopping spam...")
        
    except Exception as e:
        logger.error(f"Error in stop_spam_command: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['stats'])
def stats_command(message):
    """Show statistics"""
    try:
        user_id = message.from_user.id
        
        has_access, msg = storage.check_user_access(user_id)
        if not has_access:
            bot.send_message(message.chat.id, msg)
            return
        
        valid_sessions = len(storage.get_valid_sessions())
        total = success_count + fail_count
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        stats_text = f"""
📊 <b>BOT STATISTICS</b>

✅ Successful: {success_count}
❌ Failed: {fail_count}
📈 Success Rate: {success_rate:.1f}%

💬 Messages: {len(storage.messages)}
👥 Sessions: {valid_sessions}
📤 Total Sent: {storage.settings.get('messages_sent', 0)}

🔴 Status: {'🟢 RUNNING' if spam_active else '🔴 STOPPED'}
"""
        
        bot.send_message(message.chat.id, stats_text)
        
    except Exception as e:
        logger.error(f"Error in stats_command: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['users'])
def users_command(message):
    """View all users (Admin only)"""
    try:
        user_id = message.from_user.id
        
        if not storage.is_admin(user_id):
            bot.send_message(message.chat.id, "❌ Admin only!")
            return
        
        users = storage.users
        
        if not users:
            bot.send_message(message.chat.id, "📭 No users found!")
            return
        
        response = f"👥 <b>TOTAL USERS: {len(users)}</b>\n\n"
        
        for uid, data in list(users.items())[:20]:  # Show first 20
            username = data.get("username", "Unknown")
            is_admin = "🛡️ ADMIN" if data.get("is_admin") else "👤 USER"
            active = "✅ Active" if data.get("active") else "❌ Inactive"
            
            response += f"{is_admin} - {active}\n"
            response += f"ID: <code>{uid}</code>\n"
            response += f"Username: {username}\n"
            response += "─" * 30 + "\n\n"
        
        bot.send_message(message.chat.id, response)
        
    except Exception as e:
        logger.error(f"Error in users_command: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['broadcast'])
def broadcast_command(message):
    """Broadcast message to all users (Admin only)"""
    try:
        user_id = message.from_user.id
        
        if not storage.is_admin(user_id):
            bot.send_message(message.chat.id, "❌ Admin only!")
            return
        
        bot.send_message(
            message.chat.id,
            "📢 <b>SEND BROADCAST</b>\n\n"
            "Send the message to broadcast to all users:"
        )
        
        bot.register_next_step_handler(message, process_broadcast)
        
    except Exception as e:
        logger.error(f"Error in broadcast_command: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

def process_broadcast(message):
    """Process broadcast message"""
    try:
        user_id = message.from_user.id
        broadcast_text = message.text.strip()
        
        if not broadcast_text:
            bot.send_message(message.chat.id, "❌ Message cannot be empty!")
            return
        
        users = storage.users
        
        if not users:
            bot.send_message(message.chat.id, "❌ No users found!")
            return
        
        bot.send_message(message.chat.id, f"📤 Broadcasting to {len(users)} users...")
        
        sent = 0
        failed = 0
        
        for uid in users.keys():
            try:
                bot.send_message(
                    int(uid),
                    f"📢 <b>ANNOUNCEMENT</b>\n\n"
                    f"{broadcast_text}\n\n"
                    f"<i>Sent via {BOT_USERNAME}</i>"
                )
                sent += 1
                time.sleep(0.1)
            except:
                failed += 1
        
        bot.send_message(
            message.chat.id,
            f"✅ <b>BROADCAST COMPLETE!</b>\n\n"
            f"✅ Sent: {sent}\n"
            f"❌ Failed: {failed}\n"
            f"📊 Total: {len(users)}"
        )
        
    except Exception as e:
        logger.error(f"Error in process_broadcast: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

@bot.message_handler(commands=['addtime'])
def addtime_command(message):
    """Add time to user (Admin only)"""
    try:
        user_id = message.from_user.id
        
        if not storage.is_admin(user_id):
            bot.send_message(message.chat.id, "❌ Admin only!")
            return
        
        bot.send_message(
            message.chat.id,
            "⏰ <b>ADD TIME TO USER</b>\n\n"
            "Format: <code>user_id days</code>\n\n"
            "Example: <code>123456789 30</code>\n"
            "This adds 30 days to user 123456789"
        )
        
        bot.register_next_step_handler(message, process_addtime)
        
    except Exception as e:
        logger.error(f"Error in addtime_command: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

def process_addtime(message):
    """Process add time"""
    try:
        text = message.text.strip()
        parts = text.split()
        
        if len(parts) < 2:
            bot.send_message(message.chat.id, "❌ Invalid format!")
            return
        
        target_user_id = int(parts[0])
        days = int(parts[1])
        
        user_data = storage.get_user(target_user_id)
        if not user_data:
            bot.send_message(message.chat.id, "❌ User not found!")
            return
        
        # Update expiry
        current_expiry = datetime.fromisoformat(user_data.get("expiry"))
        new_expiry = current_expiry + timedelta(days=days)
        user_data["expiry"] = new_expiry.isoformat()
        user_data["active"] = True
        
        storage.save_file('users', storage.users)
        
        bot.send_message(
            message.chat.id,
            f"✅ <b>TIME ADDED!</b>\n\n"
            f"User: <code>{target_user_id}</code>\n"
            f"Added: {days} days\n"
            f"New expiry: {new_expiry.strftime('%Y-%m-%d %H:%M')}"
        )
        
    except Exception as e:
        logger.error(f"Error in process_addtime: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

# ========== CALLBACK HANDLERS ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    """Handle all inline keyboard callbacks"""
    try:
        user_id = call.from_user.id
        chat_id = call.message.chat.id
        message_id = call.message.message_id
        
        logger.info(f"Callback: {call.data} from {user_id}")
        
        # Answer callback query
        bot.answer_callback_query(call.id)
        
        # Handle callbacks
        if call.data == "main_menu":
            try:
                bot.delete_message(chat_id, message_id)
            except:
                pass
            start_command(call.message)
        
        elif call.data == "admin_panel":
            try:
                bot.delete_message(chat_id, message_id)
            except:
                pass
            admin_command(call.message)
        
        elif call.data == "add_msg":
            try:
                bot.delete_message(chat_id, message_id)
            except:
                pass
            addmsg_command(call.message)
        
        elif call.data == "list_msg":
            try:
                bot.delete_message(chat_id, message_id)
            except:
                pass
            listmsg_command(call.message)
        
        elif call.data == "add_session":
            try:
                bot.delete_message(chat_id, message_id)
            except:
                pass
            addsession_command(call.message)
        
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
        
        elif call.data == "admin_users":
            try:
                bot.delete_message(chat_id, message_id)
            except:
                pass
            users_command(call.message)
        
        elif call.data == "admin_broadcast":
            try:
                bot.delete_message(chat_id, message_id)
            except:
                pass
            broadcast_command(call.message)
        
        elif call.data == "admin_addtime":
            try:
                bot.delete_message(chat_id, message_id)
            except:
                pass
            addtime_command(call.message)
        
        elif call.data == "set_target":
            try:
                bot.delete_message(chat_id, message_id)
            except:
                pass
            bot.send_message(chat_id, "🎯 Enter target username:")
            bot.register_next_step_handler(call.message, process_set_target)
        
        elif call.data == "set_url":
            try:
                bot.delete_message(chat_id, message_id)
            except:
                pass
            bot.send_message(
                chat_id,
                "🔗 Enter Instagram URL:\n\n"
                "Format:\n"
                "• https://www.instagram.com/direct/t/THREAD_ID/\n"
                "• Or just the thread ID"
            )
            bot.register_next_step_handler(call.message, process_set_url)
        
        elif call.data == "set_delay":
            keyboard = InlineKeyboardMarkup(row_width=2)
            
            keyboard.add(
                InlineKeyboardButton("⚡ 1-2s", callback_data="delay_1_2"),
                InlineKeyboardButton("🚀 2-3s", callback_data="delay_2_3"),
                InlineKeyboardButton("🐇 3-5s", callback_data="delay_3_5"),
                InlineKeyboardButton("🐢 5-10s", callback_data="delay_5_10"),
                InlineKeyboardButton("🔙 Back", callback_data="setup")
            )
            
            bot.edit_message_text(
                "⏱️ Select delay:",
                chat_id,
                message_id,
                reply_markup=keyboard
            )
        
        elif call.data.startswith("delay_"):
            delays = call.data.split("_")[1:]
            if len(delays) == 2:
                storage.settings["delay_min"] = int(delays[0])
                storage.settings["delay_max"] = int(delays[1])
                storage.save_file('settings', storage.settings)
                
                bot.send_message(chat_id, f"✅ Delay set to {delays[0]}-{delays[1]}s")
                setup_command(call.message)
        
    except Exception as e:
        logger.error(f"Error in handle_callbacks: {e}")
        try:
            bot.send_message(chat_id, f"❌ Callback error: {str(e)}")
        except:
            pass

def process_set_target(message):
    """Process target setting"""
    try:
        target = message.text.strip()
        if target:
            storage.settings["target"] = target
            storage.save_file('settings', storage.settings)
            bot.send_message(message.chat.id, f"✅ Target set to: {target}")
            setup_command(message)
        else:
            bot.send_message(message.chat.id, "❌ Target cannot be empty!")
            setup_command(message)
    except Exception as e:
        logger.error(f"Error in process_set_target: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

def process_set_url(message):
    """Process URL setting"""
    try:
        url = message.text.strip()
        if not url:
            bot.send_message(message.chat.id, "❌ URL cannot be empty!")
            setup_command(message)
            return
        
        thread_id = extract_thread_id(url)
        
        storage.settings["dm_url"] = url
        if thread_id:
            storage.settings["thread_id"] = thread_id
        
        storage.save_file('settings', storage.settings)
        
        if thread_id:
            bot.send_message(
                message.chat.id,
                f"✅ <b>URL SET!</b>\n\n"
                f"Thread ID: <code>{thread_id}</code>"
            )
        else:
            bot.send_message(
                message.chat.id,
                "⚠️ URL saved but thread ID not detected"
            )
        
        setup_command(message)
        
    except Exception as e:
        logger.error(f"Error in process_set_url: {e}")
        bot.send_message(message.chat.id, f"❌ Error: {str(e)}")

# ========== ERROR HANDLER ==========
@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    """Handle other messages"""
    try:
        user_id = message.from_user.id
        
        # Auto-register user
        if not storage.get_user(user_id):
            username = message.from_user.username or message.from_user.first_name or f"user_{user_id}"
            storage.add_user(user_id, username)
        
        # If it starts with / but we don't handle it
        if message.text and message.text.startswith('/'):
            bot.send_message(
                message.chat.id,
                "❌ <b>Unknown command!</b>\n\n"
                "Use /start to see available commands."
            )
        
    except Exception as e:
        logger.error(f"Error in handle_other_messages: {e}")

# ========== MAIN FUNCTION ==========
def main():
    """Main function to start the bot"""
    print(f"""
╔════════════════════════════════════════════╗
║     INSTAGRAM SPAM BOT - WORKING VERSION  ║
║     ADMIN: {ADMIN_IDS[0]}                    ║
║     BOT: {BOT_USERNAME}                     ║
╚════════════════════════════════════════════╝
    """)
    
    # Test bot connection
    try:
        bot_info = bot.get_me()
        print(f"✅ Bot connected: @{bot_info.username}")
        print(f"✅ Bot ID: {bot_info.id}")
        print(f"✅ Bot Name: {bot_info.first_name}")
    except Exception as e:
        print(f"❌ Bot connection failed: {e}")
        return
    
    print(f"\n📊 Data loaded:")
    print(f"   • Users: {len(storage.users)}")
    print(f"   • Messages: {len(storage.messages)}")
    print(f"   • Sessions: {len(storage.sessions)}")
    print(f"   • Valid sessions: {len(storage.get_valid_sessions())}")
    
    print(f"\n🔑 Admin check:")
    for admin_id in ADMIN_IDS:
        if storage.is_admin(admin_id):
            print(f"   ✅ Admin {admin_id} is registered")
        else:
            print(f"   ❌ Admin {admin_id} NOT registered!")
    
    print(f"\n{'='*60}")
    print("📋 Commands available:")
    print("   User: /start, /addmsg, /addsession, /setup, /start_spam")
    print("   Admin: /admin, /users, /broadcast, /addtime")
    print(f"{'='*60}")
    print("🚀 Bot is starting...")
    print("Press Ctrl+C to stop")
    print(f"{'='*60}\n")
    
    # Start bot
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Bot error: {e}")
    finally:
        # Save data before exit
        storage.save_all()
        print("💾 Data saved")

if __name__ == "__main__":
    main()
