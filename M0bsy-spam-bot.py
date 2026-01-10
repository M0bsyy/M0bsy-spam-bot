#!/usr/bin/env python3
"""
COMPLETE INSTAGRAM SPAM BOT WITH ADMIN PANEL
Fixed and Enhanced Version
Author: M0bsy
GitHub: https://github.com/M0bsyy/M0bsy-spam-bot.git
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
import asyncio
import string
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import telebot
from telebot.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    CallbackQuery,
    Message
)
from telebot import apihelper, types
from telebot.custom_filters import AdvancedCustomFilter
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup

# ========== SETUP LOGGING ==========
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ========== CONFIGURATION ==========
# BOT TOKEN (Replace with your actual token)
TELEGRAM_BOT_TOKEN = "8595686704:AAGZ6-f7cjiaET1J2yXM-QBuJCq_fyOMJ7o"

# IMPORTANT: This is YOUR Telegram User ID (you can get it from @userinfobot)
ADMIN_USER_IDS = [6107382622]  # Add multiple admins if needed

# Bot Info
BOT_USERNAME = "@M0bsy_spam_bot"
CONTACT_USERNAME = "@M0bsy_olds"

# Bot Settings
MAX_MESSAGES = 500
MAX_SESSIONS = 50
RATE_LIMIT_DELAY = 0.5  # seconds between messages
MAX_BROADCAST_USERS = 1000

# File Paths
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = BASE_DIR / "backups"

# Create directories
DATA_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)

# ========== INITIALIZE BOT ==========
# Use state storage for better management
state_storage = StateMemoryStorage()
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML", state_storage=state_storage)

# ========== STATE MANAGEMENT ==========
class BotStates(StatesGroup):
    add_message = State()
    add_session = State()
    set_target = State()
    set_url = State()
    set_delay = State()
    broadcast_message = State()
    add_time_user = State()
    delete_user = State()
    edit_message = State()
    admin_broadcast = State()

# ========== DATA MODELS ==========
class User:
    def __init__(self, user_id: int, username: str = "", is_admin: bool = False):
        self.id = user_id
        self.username = username or f"user_{user_id}"
        self.is_admin = is_admin
        self.plan = "trial"
        self.expiry = datetime.now() + timedelta(hours=1)
        self.joined = datetime.now()
        self.active = True
        self.message_count = 0
        self.last_activity = datetime.now()
        
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "is_admin": self.is_admin,
            "plan": self.plan,
            "expiry": self.expiry.isoformat(),
            "joined": self.joined.isoformat(),
            "active": self.active,
            "message_count": self.message_count,
            "last_activity": self.last_activity.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        user = cls(
            user_id=data["id"],
            username=data.get("username", ""),
            is_admin=data.get("is_admin", False)
        )
        user.plan = data.get("plan", "trial")
        user.expiry = datetime.fromisoformat(data["expiry"])
        user.joined = datetime.fromisoformat(data["joined"])
        user.active = data.get("active", True)
        user.message_count = data.get("message_count", 0)
        user.last_activity = datetime.fromisoformat(data.get("last_activity", datetime.now().isoformat()))
        return user

class InstagramSession:
    def __init__(self, session_id: str, username: str = ""):
        self.session_id = session_id
        self.username = username or "unknown"
        self.status = "pending"
        self.added = datetime.now()
        self.last_used = datetime.now()
        self.message_count = 0
        self.success_count = 0
        self.fail_count = 0
        
    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "username": self.username,
            "status": self.status,
            "added": self.added.isoformat(),
            "last_used": self.last_used.isoformat(),
            "message_count": self.message_count,
            "success_count": self.success_count,
            "fail_count": self.fail_count
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'InstagramSession':
        session = cls(
            session_id=data["session_id"],
            username=data.get("username", "")
        )
        session.status = data.get("status", "pending")
        session.added = datetime.fromisoformat(data["added"])
        session.last_used = datetime.fromisoformat(data["last_used"])
        session.message_count = data.get("message_count", 0)
        session.success_count = data.get("success_count", 0)
        session.fail_count = data.get("fail_count", 0)
        return session

class SpamMessage:
    def __init__(self, text: str, author_id: int):
        self.id = hashlib.md5(f"{text}{author_id}{time.time()}".encode()).hexdigest()[:8]
        self.text = text
        self.author_id = author_id
        self.created = datetime.now()
        self.used_count = 0
        
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "author_id": self.author_id,
            "created": self.created.isoformat(),
            "used_count": self.used_count
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'SpamMessage':
        msg = cls(
            text=data["text"],
            author_id=data["author_id"]
        )
        msg.id = data["id"]
        msg.created = datetime.fromisoformat(data["created"])
        msg.used_count = data.get("used_count", 0)
        return msg

# ========== DATA MANAGER ==========
class DataManager:
    def __init__(self):
        self.users_file = DATA_DIR / "users.json"
        self.sessions_file = DATA_DIR / "sessions.json"
        self.messages_file = DATA_DIR / "messages.json"
        self.settings_file = DATA_DIR / "settings.json"
        self.stats_file = DATA_DIR / "stats.json"
        
        self.users: Dict[int, User] = {}
        self.sessions: List[InstagramSession] = []
        self.messages: List[SpamMessage] = []
        self.settings: Dict[str, Any] = {}
        self.stats: Dict[str, Any] = {}
        
        self.load_all_data()
        self.initialize_admin()
    
    def load_all_data(self):
        """Load all data from files"""
        try:
            # Load users
            if self.users_file.exists():
                with open(self.users_file, 'r', encoding='utf-8') as f:
                    users_data = json.load(f)
                    self.users = {int(uid): User.from_dict(data) for uid, data in users_data.items()}
            logger.info(f"Loaded {len(self.users)} users")
            
            # Load sessions
            if self.sessions_file.exists():
                with open(self.sessions_file, 'r', encoding='utf-8') as f:
                    sessions_data = json.load(f)
                    self.sessions = [InstagramSession.from_dict(data) for data in sessions_data]
            logger.info(f"Loaded {len(self.sessions)} sessions")
            
            # Load messages
            if self.messages_file.exists():
                with open(self.messages_file, 'r', encoding='utf-8') as f:
                    messages_data = json.load(f)
                    self.messages = [SpamMessage.from_dict(data) for data in messages_data]
            logger.info(f"Loaded {len(self.messages)} messages")
            
            # Load settings
            if self.settings_file.exists():
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            
            # Load stats
            if self.stats_file.exists():
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    self.stats = json.load(f)
                    
        except Exception as e:
            logger.error(f"Error loading data: {e}")
            self.initialize_defaults()
    
    def save_all_data(self):
        """Save all data to files"""
        try:
            # Save users
            users_data = {str(uid): user.to_dict() for uid, user in self.users.items()}
            with open(self.users_file, 'w', encoding='utf-8') as f:
                json.dump(users_data, f, indent=2, ensure_ascii=False)
            
            # Save sessions
            sessions_data = [session.to_dict() for session in self.sessions]
            with open(self.sessions_file, 'w', encoding='utf-8') as f:
                json.dump(sessions_data, f, indent=2, ensure_ascii=False)
            
            # Save messages
            messages_data = [message.to_dict() for message in self.messages]
            with open(self.messages_file, 'w', encoding='utf-8') as f:
                json.dump(messages_data, f, indent=2, ensure_ascii=False)
            
            # Save settings
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            
            # Save stats
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
                
            logger.debug("All data saved successfully")
        except Exception as e:
            logger.error(f"Error saving data: {e}")
    
    def backup_data(self):
        """Create backup of all data"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = BACKUP_DIR / timestamp
            backup_dir.mkdir(exist_ok=True)
            
            # Copy all data files
            import shutil
            for file in [self.users_file, self.sessions_file, self.messages_file, 
                        self.settings_file, self.stats_file]:
                if file.exists():
                    shutil.copy2(file, backup_dir / file.name)
            
            logger.info(f"Backup created: {backup_dir}")
            return True
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return False
    
    def initialize_defaults(self):
        """Initialize default settings"""
        self.settings = {
            "target": "instagram_user",
            "delay_min": 2,
            "delay_max": 5,
            "dm_url": "",
            "continuous_mode": True,
            "messages_sent": 0,
            "spam_active": False,
            "current_thread_id": "",
            "max_sessions_per_user": 5,
            "rate_limit": 1.0
        }
        
        self.stats = {
            "total_messages_sent": 0,
            "successful_messages": 0,
            "failed_messages": 0,
            "total_users": 0,
            "active_users": 0,
            "bot_start_time": datetime.now().isoformat(),
            "uptime_days": 0
        }
    
    def initialize_admin(self):
        """Initialize admin accounts"""
        for admin_id in ADMIN_USER_IDS:
            if admin_id not in self.users:
                admin_user = User(admin_id, "ADMIN", is_admin=True)
                admin_user.plan = "lifetime_admin"
                admin_user.expiry = datetime.now() + timedelta(days=36500)
                self.users[admin_id] = admin_user
                logger.info(f"Admin initialized: {admin_id}")
        
        self.save_all_data()
    
    def add_user(self, user_id: int, username: str = "") -> User:
        """Add new user or update existing"""
        if user_id in self.users:
            user = self.users[user_id]
            user.username = username or user.username
            user.last_activity = datetime.now()
        else:
            is_admin = user_id in ADMIN_USER_IDS
            user = User(user_id, username, is_admin)
            self.users[user_id] = user
            logger.info(f"New user added: {user_id} ({username})")
        
        self.save_all_data()
        return user
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        if user_id in ADMIN_USER_IDS:
            return True
        
        user = self.get_user(user_id)
        return user.is_admin if user else False
    
    def check_user_access(self, user_id: int) -> Tuple[bool, str]:
        """Check if user has access"""
        if user_id in ADMIN_USER_IDS:
            return True, "✅ Admin access"
        
        user = self.get_user(user_id)
        if not user:
            return False, "❌ User not registered"
        
        if not user.active:
            return False, "❌ Account deactivated"
        
        if datetime.now() > user.expiry:
            user.active = False
            self.save_all_data()
            return False, "❌ Trial expired"
        
        return True, "✅ Access granted"
    
    def add_time_to_user(self, user_id: int, amount: int, unit: str) -> bool:
        """Add time to user account"""
        user = self.get_user(user_id)
        if not user:
            return False
        
        current_expiry = user.expiry if datetime.now() < user.expiry else datetime.now()
        
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
            user.plan = "lifetime"
        else:
            return False
        
        user.expiry = new_expiry
        user.active = True
        self.save_all_data()
        return True
    
    def get_all_users(self) -> List[User]:
        """Get all users"""
        return list(self.users.values())
    
    def get_active_users(self) -> List[User]:
        """Get active users"""
        active_users = []
        now = datetime.now()
        for user in self.users.values():
            if user.active and now < user.expiry:
                active_users.append(user)
        return active_users
    
    def get_valid_sessions(self) -> List[InstagramSession]:
        """Get valid Instagram sessions"""
        return [s for s in self.sessions if s.status == "valid"]
    
    def add_session(self, session_id: str, username: str = "") -> InstagramSession:
        """Add new Instagram session"""
        session = InstagramSession(session_id, username)
        self.sessions.append(session)
        self.save_all_data()
        return session
    
    def update_session_status(self, session_id: str, status: str, username: str = ""):
        """Update session status"""
        for session in self.sessions:
            if session.session_id == session_id:
                session.status = status
                session.username = username or session.username
                session.last_used = datetime.now()
                break
        self.save_all_data()
    
    def add_message(self, text: str, author_id: int) -> SpamMessage:
        """Add spam message"""
        if len(self.messages) >= MAX_MESSAGES:
            # Remove oldest message
            self.messages.pop(0)
        
        message = SpamMessage(text, author_id)
        self.messages.append(message)
        self.save_all_data()
        return message
    
    def delete_message(self, message_id: str) -> bool:
        """Delete message by ID"""
        for i, msg in enumerate(self.messages):
            if msg.id == message_id:
                self.messages.pop(i)
                self.save_all_data()
                return True
        return False
    
    def get_random_message(self) -> Optional[str]:
        """Get random spam message"""
        if not self.messages:
            return None
        
        msg = random.choice(self.messages)
        msg.used_count += 1
        self.save_all_data()
        return msg.text
    
    def update_stats(self, key: str, value: Any = None, increment: int = 1):
        """Update statistics"""
        if key not in self.stats:
            self.stats[key] = 0
        
        if value is not None:
            self.stats[key] = value
        else:
            self.stats[key] = self.stats.get(key, 0) + increment
        
        self.save_all_data()

# ========== GLOBAL INSTANCES ==========
data_manager = DataManager()

# Spam control variables
spam_active = False
spam_thread = None
success_count = 0
fail_count = 0
total_sent = 0
spam_lock = threading.Lock()

# ========== INSTAGRAM API FUNCTIONS ==========
def validate_instagram_session(session_id: str) -> Tuple[bool, str, str]:
    """Validate Instagram session"""
    try:
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        # Method 1: Check user profile
        response = requests.get(
            'https://www.instagram.com/api/v1/users/web_profile_info/?username=instagram',
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('status') == 'ok':
                    # Try to get username
                    username = "instagram_user"
                    if 'data' in data and 'user' in data['data']:
                        username = data['data']['user'].get('username', 'instagram_user')
                    return True, username, "✅ Valid session"
            except:
                pass
        
        # Method 2: Check edit page
        response = requests.get(
            'https://www.instagram.com/accounts/edit/',
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200:
            import re
            content = response.text.lower()
            if 'instagram' in content:
                # Extract username
                username = "instagram_user"
                match = re.search(r'"username":"([^"]+)"', response.text)
                if match:
                    username = match.group(1)
                return True, username, "✅ Valid session"
        
        # Method 3: Check direct inbox
        response = requests.get(
            'https://www.instagram.com/direct/inbox/',
            headers=headers,
            timeout=15
        )
        
        if response.status_code == 200 and 'direct_v2' in response.text:
            return True, "instagram_user", "✅ Valid session"
        
        return False, "", "❌ Invalid session ID or expired"
        
    except requests.exceptions.Timeout:
        return False, "", "❌ Connection timeout"
    except requests.exceptions.ConnectionError:
        return False, "", "❌ Connection error"
    except Exception as e:
        logger.error(f"Session validation error: {e}")
        return False, "", f"❌ Error: {str(e)}"

def send_instagram_dm(session_id: str, thread_id: str, message: str) -> Tuple[bool, str]:
    """Send Instagram Direct Message"""
    try:
        # First, get CSRF token
        headers = {
            'cookie': f'sessionid={session_id}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        response = requests.get(
            'https://www.instagram.com/',
            headers=headers,
            timeout=15
        )
        
        csrf_token = ""
        if response.status_code == 200:
            import re
            matches = re.findall(r'"csrf_token":"([^"]+)"', response.text)
            if matches:
                csrf_token = matches[0]
        
        if not csrf_token:
            # Try alternative method
            csrf_token = "missing"
            for cookie in response.cookies:
                if cookie.name == 'csrftoken':
                    csrf_token = cookie.value
                    break
        
        # Prepare headers for API request
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
        
        # Generate unique client context
        timestamp = int(time.time() * 1000)
        client_context = f"{timestamp}"
        device_id = f"android-{hashlib.md5(str(timestamp).encode()).hexdigest()[:16]}"
        
        # Prepare data
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
        
        # Send message
        response = requests.post(
            'https://www.instagram.com/api/v1/direct_v2/threads/broadcast/text/',
            headers=headers,
            data=data,
            timeout=20
        )
        
        if response.status_code == 200:
            try:
                resp_json = response.json()
                if resp_json.get('status') == 'ok':
                    return True, "✅ Message sent successfully"
                else:
                    return False, f"❌ Instagram error: {resp_json.get('message', 'Unknown')}"
            except:
                return True, "✅ Message sent (no confirmation)"
        elif response.status_code == 400:
            return False, "❌ Bad request - check thread ID"
        elif response.status_code == 403:
            return False, "❌ Session expired or banned"
        elif response.status_code == 429:
            return False, "❌ Rate limited - too many requests"
        else:
            return False, f"❌ HTTP {response.status_code}: {response.text[:100]}"
            
    except requests.exceptions.Timeout:
        return False, "❌ Request timeout"
    except requests.exceptions.ConnectionError:
        return False, "❌ Connection error"
    except Exception as e:
        logger.error(f"Send DM error: {e}")
        return False, f"❌ Error: {str(e)}"

def extract_thread_id(url: str) -> Optional[str]:
    """Extract thread ID from Instagram URL"""
    try:
        url = url.strip()
        
        # If it's already a numeric ID
        if url.isdigit() and len(url) > 8:
            return url
        
        # Extract from direct URL
        patterns = [
            r'/direct/t/([0-9]+)',
            r'thread_id=([0-9]+)',
            r't/([0-9]+)',
            r'([0-9]{15,})'  # Instagram IDs are usually 15+ digits
        ]
        
        import re
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        return None
    except Exception as e:
        logger.error(f"Error extracting thread ID: {e}")
        return None

# ========== DECORATORS & FILTERS ==========
def admin_required(func):
    """Decorator to restrict access to admins only"""
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        
        # Check if user is admin
        if not data_manager.is_admin(user_id):
            logger.warning(f"Non-admin access attempt: {user_id}")
            bot.reply_to(message, 
                "🔒 <b>ACCESS DENIED!</b>\n\n"
                "This command is for administrators only.\n"
                f"Your ID: <code>{user_id}</code>\n"
                f"Admin IDs: {', '.join(map(str, ADMIN_USER_IDS))}"
            )
            return
        
        # User is admin, proceed with function
        return func(message, *args, **kwargs)
    return wrapper

def user_access_required(func):
    """Decorator to check user access"""
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id
        
        # Always allow start command
        if message.text and message.text.startswith('/start'):
            return func(message, *args, **kwargs)
        
        # Check access
        has_access, msg = data_manager.check_user_access(user_id)
        
        if not has_access:
            if "expired" in msg:
                bot.reply_to(message,
                    "⏰ <b>TRIAL EXPIRED!</b>\n\n"
                    "Your trial period has ended.\n"
                    f"Contact {CONTACT_USERNAME} for premium access.\n\n"
                    "🔑 Want lifetime access? DM for pricing!"
                )
            elif "not registered" in msg:
                # Auto-register new users
                username = message.from_user.username or message.from_user.first_name or f"user_{user_id}"
                data_manager.add_user(user_id, username)
                bot.reply_to(message,
                    "👋 <b>WELCOME!</b>\n\n"
                    "You've been registered with 1-hour trial.\n"
                    "Use /start to see all commands.\n\n"
                    "⚠️ Note: This is a trial version with limited features."
                )
            else:
                bot.reply_to(message, msg)
            return
        
        # Access granted
        return func(message, *args, **kwargs)
    return wrapper

# ========== SPAM WORKER ==========
def spam_worker(chat_id: int, thread_id: str, user_id: int):
    """Main spam worker function"""
    global spam_active, success_count, fail_count, total_sent
    
    logger.info(f"Spam worker started for user {user_id}")
    
    try:
        # Get settings
        settings = data_manager.settings
        target = settings.get("target", "user")
        delay_min = settings.get("delay_min", 2)
        delay_max = settings.get("delay_max", 5)
        
        # Get valid sessions
        valid_sessions = data_manager.get_valid_sessions()
        if not valid_sessions:
            bot.send_message(chat_id, "❌ No valid sessions available!")
            spam_active = False
            return
        
        # Get messages
        messages = data_manager.messages
        if not messages:
            bot.send_message(chat_id, "❌ No messages available!")
            spam_active = False
            return
        
        # Send initial status
        status_msg = bot.send_message(chat_id,
            f"🚀 <b>SPAM STARTED!</b>\n\n"
            f"🎯 Target: {target}\n"
            f"🔗 Thread ID: <code>{thread_id}</code>\n"
            f"📝 Messages: {len(messages)}\n"
            f"👥 Sessions: {len(valid_sessions)}\n"
            f"⏱️ Delay: {delay_min}-{delay_max}s\n\n"
            f"<i>Starting spam process...</i>"
        )
        
        session_index = 0
        message_counter = 0
        last_update = time.time()
        
        # Main spam loop
        while spam_active:
            try:
                # Check user access every 10 messages
                if message_counter % 10 == 0:
                    has_access, access_msg = data_manager.check_user_access(user_id)
                    if not has_access:
                        bot.send_message(chat_id, f"⏰ <b>ACCESS TERMINATED!</b>\n\n{access_msg}")
                        spam_active = False
                        break
                
                # Get random message
                message_text = data_manager.get_random_message()
                if not message_text:
                    logger.error("No messages available")
                    break
                
                # Format message with target
                formatted_message = message_text.replace("{target}", target)
                
                # Get session (round-robin)
                session = valid_sessions[session_index % len(valid_sessions)]
                session_id = session.session_id
                session_username = session.username
                
                # Send message
                success, result = send_instagram_dm(session_id, thread_id, formatted_message)
                
                with spam_lock:
                    total_sent += 1
                    message_counter += 1
                    data_manager.settings["messages_sent"] = total_sent
                    
                    if success:
                        success_count += 1
                        session.success_count += 1
                        data_manager.update_stats("successful_messages")
                    else:
                        fail_count += 1
                        session.fail_count += 1
                        data_manager.update_stats("failed_messages")
                    
                    session.message_count += 1
                    session.last_used = datetime.now()
                
                data_manager.save_all_data()
                
                # Update session index
                session_index += 1
                
                # Send progress update every 30 seconds
                current_time = time.time()
                if current_time - last_update >= 30:
                    total = success_count + fail_count
                    success_rate = (success_count / total * 100) if total > 0 else 0
                    
                    progress_msg = f"""
📊 <b>SPAM PROGRESS UPDATE</b>

✅ Messages Sent: {message_counter}
✅ Successful: {success_count}
❌ Failed: {fail_count}
📈 Success Rate: {success_rate:.1f}%
👥 Current Session: {session_username}

<i>Spam is running... Use /stop_spam to stop</i>
"""
                    try:
                        bot.edit_message_text(
                            progress_msg,
                            chat_id=chat_id,
                            message_id=status_msg.message_id
                        )
                    except:
                        pass
                    
                    last_update = current_time
                
                # Random delay between messages
                delay = random.uniform(delay_min, delay_max)
                time.sleep(delay)
                
                # Random session validation every 50 messages
                if message_counter % 50 == 0:
                    logger.info(f"Validating sessions after {message_counter} messages")
                    # Re-validate sessions in background
                    
            except Exception as e:
                logger.error(f"Error in spam loop: {e}")
                time.sleep(5)  # Wait before retrying
                
    except Exception as e:
        logger.error(f"Critical error in spam worker: {e}")
        bot.send_message(chat_id, f"❌ <b>SPAM ERROR!</b>\n\nError: {str(e)}")
    finally:
        spam_active = False
        
        # Send final report
        total = success_count + fail_count
        success_rate = (success_count / total * 100) if total > 0 else 0
        
        final_report = f"""
🛑 <b>SPAM STOPPED</b>

📊 <b>FINAL REPORT</b>

✅ Successful Messages: {success_count}
❌ Failed Messages: {fail_count}
📈 Success Rate: {success_rate:.1f}%
📤 Total Sent: {message_counter}

🎯 Target: {settings.get('target', 'N/A')}
🔗 Thread ID: {thread_id}

<i>Spam session completed.</i>
"""
        
        try:
            bot.send_message(chat_id, final_report)
        except:
            pass
        
        logger.info(f"Spam worker stopped. Sent {message_counter} messages")

# ========== COMMAND HANDLERS ==========
@bot.message_handler(commands=['start'])
@user_access_required
def start_command(message: Message):
    """Handle /start command"""
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or "User"
    
    logger.info(f"Start command from {user_id} ({username})")
    
    # Add/update user
    user = data_manager.add_user(user_id, username)
    
    # Get bot info
    try:
        bot_info = bot.get_me()
        bot_username = f"@{bot_info.username}"
    except:
        bot_username = BOT_USERNAME
    
    # Check if admin
    is_admin = data_manager.is_admin(user_id)
    
    # Get stats
    valid_sessions = len(data_manager.get_valid_sessions())
    active_users = len(data_manager.get_active_users())
    total_messages = len(data_manager.messages)
    
    welcome_text = f"""
╔════════════════════════════════════════════╗
║     INSTAGRAM SPAM BOT v4.0              ║
║     POWERED BY M0BSY                      ║
╚════════════════════════════════════════════╝

👤 <b>User:</b> {username}
🆔 <b>ID:</b> <code>{user_id}</code>
{'🛡️ <b>Status:</b> ✅ ADMIN (Lifetime Access)' if is_admin else '👤 <b>Status:</b> Trial User'}
⏰ <b>Expiry:</b> {user.expiry.strftime('%Y-%m-%d %H:%M')}

📊 <b>SYSTEM STATISTICS:</b>
• Messages: {total_messages}
• Valid Sessions: {valid_sessions}
• Active Users: {active_users}
• Total Sent: {data_manager.settings.get('messages_sent', 0)}
• Spam Status: {'🟢 RUNNING' if spam_active else '🔴 STOPPED'}

📋 <b>MAIN COMMANDS:</b>
• /addmsg - Add spam message
• /listmsg - List all messages
• /addsession - Add Instagram session
• /sessions - View all sessions
• /setup - Configure spam settings
• /start_spam - 🚀 Start continuous spam
• /stop_spam - 🛑 Stop spam
• /stats - View statistics

{'🔐 <b>ADMIN COMMANDS:</b>' if is_admin else ''}
{'• /admin - Admin control panel' if is_admin else ''}
{'• /users - View all users' if is_admin else ''}
{'• /broadcast - Send message to all users' if is_admin else ''}
{'• /addtime - Add time to user' if is_admin else ''}
{'• /backup - Create backup' if is_admin else ''}

💡 <b>TIPS:</b>
• Use {target} in messages for target username
• Add multiple sessions for better performance
• Set proper delays to avoid bans
"""
    
    # Create inline keyboard
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    # Main buttons
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
    
    # Admin button if admin
    if is_admin:
        keyboard.add(
            InlineKeyboardButton("🔐 ADMIN PANEL", callback_data="admin_panel"),
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")
        )
    
    # Contact button
    keyboard.add(
        InlineKeyboardButton("📞 Contact Owner", url=f"https://t.me/{CONTACT_USERNAME.replace('@', '')}")
    )
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )

@bot.message_handler(commands=['admin'])
@admin_required
def admin_command(message: Message):
    """Admin control panel"""
    user_id = message.from_user.id
    
    logger.info(f"Admin panel accessed by {user_id}")
    
    # Get stats
    total_users = len(data_manager.users)
    active_users = len(data_manager.get_active_users())
    valid_sessions = len(data_manager.get_valid_sessions())
    total_messages = len(data_manager.messages)
    
    admin_text = f"""
🔐 <b>ADMINISTRATOR CONTROL PANEL</b>

🛡️ <b>Welcome, Admin!</b>
🆔 <b>Your ID:</b> <code>{user_id}</code>
🤖 <b>Bot:</b> {BOT_USERNAME}

📊 <b>SYSTEM OVERVIEW:</b>
• Total Users: {total_users}
• Active Users: {active_users}
• Valid Sessions: {valid_sessions}
• Total Messages: {total_messages}
• Messages Sent: {data_manager.settings.get('messages_sent', 0)}
• Spam Active: {'🟢 YES' if spam_active else '🔴 NO'}

⚙️ <b>ADMIN ACTIONS:</b>
"""
    
    # Create admin keyboard
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    keyboard.add(
        InlineKeyboardButton("👥 View All Users", callback_data="admin_users"),
        InlineKeyboardButton("📊 System Stats", callback_data="admin_stats"),
        InlineKeyboardButton("📢 Broadcast Message", callback_data="admin_broadcast"),
        InlineKeyboardButton("⏰ Add User Time", callback_data="admin_addtime"),
        InlineKeyboardButton("🗑️ Delete User", callback_data="admin_deleteuser"),
        InlineKeyboardButton("💾 Create Backup", callback_data="admin_backup"),
        InlineKeyboardButton("🔄 Refresh Data", callback_data="admin_refresh"),
        InlineKeyboardButton("📝 Edit Settings", callback_data="admin_settings"),
        InlineKeyboardButton("🚫 Ban User", callback_data="admin_banuser"),
        InlineKeyboardButton("✅ Unban User", callback_data="admin_unbanuser"),
        InlineKeyboardButton("📋 User Details", callback_data="admin_userdetails"),
        InlineKeyboardButton("📈 Advanced Stats", callback_data="admin_advancedstats")
    )
    
    keyboard.add(
        InlineKeyboardButton("◀️ Main Menu", callback_data="main_menu")
    )
    
    bot.send_message(
        message.chat.id,
        admin_text,
        reply_markup=keyboard
    )

@bot.message_handler(commands=['addmsg'])
@user_access_required
def addmsg_command(message: Message):
    """Add spam message"""
    user_id = message.from_user.id
    
    bot.send_message(
        message.chat.id,
        "✍️ <b>Send your spam message:</b>\n\n"
        "Use <code>{target}</code> to insert target username\n"
        "Example: Hello {target}! 👋 How are you today?\n\n"
        "⚠️ <i>Maximum 1000 characters</i>"
    )
    
    bot.set_state(user_id, BotStates.add_message, message.chat.id)

@bot.message_handler(state=BotStates.add_message)
def process_add_message(message: Message):
    """Process new message"""
    user_id = message.from_user.id
    
    with bot.retrieve_data(user_id, message.chat.id) as data:
        pass  # State data not needed here
    
    text = message.text.strip()
    
    if not text:
        bot.send_message(message.chat.id, "❌ Message cannot be empty!")
        bot.delete_state(user_id, message.chat.id)
        return
    
    if len(text) > 1000:
        bot.send_message(message.chat.id, "❌ Message too long! Max 1000 characters.")
        bot.delete_state(user_id, message.chat.id)
        return
    
    # Add message
    spam_message = data_manager.add_message(text, user_id)
    
    bot.send_message(
        message.chat.id,
        f"✅ <b>Message added successfully!</b>\n\n"
        f"📝 <b>Preview:</b> {text[:100]}...\n"
        f"🆔 <b>Message ID:</b> <code>{spam_message.id}</code>\n"
        f"📊 <b>Total messages:</b> {len(data_manager.messages)}\n\n"
        f"<i>Use /listmsg to see all messages</i>"
    )
    
    bot.delete_state(user_id, message.chat.id)

@bot.message_handler(commands=['listmsg'])
@user_access_required
def listmsg_command(message: Message):
    """List all spam messages"""
    messages = data_manager.messages
    
    if not messages:
        bot.send_message(message.chat.id, "📭 <b>No messages found!</b>")
        return
    
    response = "📋 <b>AVAILABLE MESSAGES:</b>\n\n"
    
    for i, msg in enumerate(messages, 1):
        preview = msg.text[:50] + "..." if len(msg.text) > 50 else msg.text
        response += f"{i}. <code>{preview}</code>\n"
        response += f"   👤 Author: {msg.author_id} | 🔢 Used: {msg.used_count}x\n\n"
    
    response += f"📊 <b>Total:</b> {len(messages)} messages"
    
    # Add delete buttons for admins
    if data_manager.is_admin(message.from_user.id):
        keyboard = InlineKeyboardMarkup(row_width=2)
        for i, msg in enumerate(messages[:10], 1):  # Show first 10
            keyboard.add(
                InlineKeyboardButton(f"🗑️ Delete {i}", callback_data=f"delete_msg_{msg.id}")
            )
        keyboard.add(
            InlineKeyboardButton("📋 View All", callback_data="view_all_messages")
        )
        
        bot.send_message(
            message.chat.id,
            response,
            reply_markup=keyboard
        )
    else:
        bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['addsession'])
@user_access_required
def addsession_command(message: Message):
    """Add Instagram session"""
    user_id = message.from_user.id
    
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
<code>sessionid=YOUR_SESSION_ID_HERE</code>

⚠️ <i>Make sure the session is from a logged-in Instagram account</i>
"""
    
    bot.send_message(message.chat.id, instruction)
    bot.set_state(user_id, BotStates.add_session, message.chat.id)

@bot.message_handler(state=BotStates.add_session)
def process_add_session(message: Message):
    """Process new session"""
    user_id = message.from_user.id
    
    with bot.retrieve_data(user_id, message.chat.id) as data:
        pass
    
    session_text = message.text.strip()
    
    # Extract session ID
    session_id = ""
    if "sessionid=" in session_text:
        session_id = session_text.split("sessionid=")[1].split(";")[0].strip()
    else:
        session_id = session_text.strip()
    
    if len(session_id) < 20:
        bot.send_message(message.chat.id, "❌ Invalid session ID! Too short.")
        bot.delete_state(user_id, message.chat.id)
        return
    
    # Validate session
    bot.send_message(message.chat.id, "🔍 <b>Validating session...</b>")
    
    valid, username, info = validate_instagram_session(session_id)
    
    if valid:
        # Add session
        session = data_manager.add_session(session_id, username)
        data_manager.update_session_status(session_id, "valid", username)
        
        valid_sessions = len(data_manager.get_valid_sessions())
        
        bot.send_message(
            message.chat.id,
            f"✅ <b>SESSION ADDED SUCCESSFULLY!</b>\n\n"
            f"👤 <b>Username:</b> {username}\n"
            f"🆔 <b>Session ID:</b> <code>{session_id[:20]}...</code>\n"
            f"🕒 <b>Added:</b> {datetime.now().strftime('%H:%M:%S')}\n"
            f"📊 <b>Valid sessions:</b> {valid_sessions}\n\n"
            f"<i>Use /sessions to view all sessions</i>"
        )
    else:
        bot.send_message(
            message.chat.id,
            f"❌ <b>SESSION VALIDATION FAILED!</b>\n\n"
            f"Reason: {info}\n\n"
            f"<b>Make sure:</b>\n"
            f"1. Session ID is correct\n"
            f"2. Instagram account is logged in\n"
            f"3. Session is not expired\n"
            f"4. Account is not banned/limited"
        )
    
    bot.delete_state(user_id, message.chat.id)

@bot.message_handler(commands=['sessions'])
@user_access_required
def sessions_command(message: Message):
    """View all Instagram sessions"""
    sessions = data_manager.sessions
    valid_sessions = data_manager.get_valid_sessions()
    
    if not sessions:
        bot.send_message(message.chat.id, "🔐 <b>No sessions found!</b>")
        return
    
    response = f"""
👥 <b>INSTAGRAM SESSIONS</b>

✅ <b>Valid Sessions:</b> {len(valid_sessions)}
❌ <b>Invalid/Expired:</b> {len(sessions) - len(valid_sessions)}
📊 <b>Total:</b> {len(sessions)}

"""
    
    if valid_sessions:
        response += "✅ <b>ACTIVE SESSIONS:</b>\n"
        for i, session in enumerate(valid_sessions[:10], 1):  # Show first 10
            last_used = datetime.fromisoformat(session.last_used.isoformat())
            time_diff = datetime.now() - last_used
            hours_diff = time_diff.total_seconds() / 3600
            
            response += f"{i}. <b>{session.username}</b>\n"
            response += f"   Messages: {session.message_count} | "
            response += f"Success: {session.success_count} | "
            response += f"Fail: {session.fail_count}\n"
            response += f"   Last used: {hours_diff:.1f} hours ago\n\n"
    
    # Show invalid sessions for admins
    if data_manager.is_admin(message.from_user.id):
        invalid_sessions = [s for s in sessions if s.status != "valid"]
        if invalid_sessions:
            response += "❌ <b>INVALID SESSIONS:</b>\n"
            for i, session in enumerate(invalid_sessions[:5], 1):
                response += f"{i}. {session.username} - {session.status}\n"
    
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['setup'])
@user_access_required
def setup_command(message: Message):
    """Setup spam configuration"""
    settings = data_manager.settings
    
    config_text = f"""
⚙️ <b>SPAM CONFIGURATION PANEL</b>

🎯 <b>Target Username:</b> {settings.get('target', 'Not set')}
🔗 <b>Instagram URL:</b> {'✅ Set' if settings.get('dm_url') else '❌ Not set'}
⏱️ <b>Delay Between Messages:</b> {settings.get('delay_min', 2)}-{settings.get('delay_max', 5)} seconds
♾️ <b>Spam Mode:</b> {'CONTINUOUS' if settings.get('continuous_mode', True) else 'LIMITED'}
📊 <b>Messages Sent (Total):</b> {settings.get('messages_sent', 0)}
🔢 <b>Max Sessions:</b> {settings.get('max_sessions_per_user', 5)}
⚡ <b>Rate Limit:</b> {settings.get('rate_limit', 1.0)} seconds

💡 <b>Instructions:</b>
1. Set target username (used in messages as {target})
2. Set Instagram DM URL or Thread ID
3. Configure delay based on safety needs
4. Start spam with /start_spam
"""
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    keyboard.add(
        InlineKeyboardButton("🎯 Set Target", callback_data="set_target"),
        InlineKeyboardButton("🔗 Set URL", callback_data="set_url"),
        InlineKeyboardButton("⏱️ Set Delay", callback_data="set_delay"),
        InlineKeyboardButton("♾️ Toggle Mode", callback_data="toggle_mode"),
        InlineKeyboardButton("⚡ Rate Limit", callback_data="set_rate_limit"),
        InlineKeyboardButton("🔢 Max Sessions", callback_data="set_max_sessions"),
        InlineKeyboardButton("📊 View Current", callback_data="view_settings"),
        InlineKeyboardButton("🔄 Reset Defaults", callback_data="reset_settings")
    )
    
    keyboard.add(
        InlineKeyboardButton("◀️ Main Menu", callback_data="main_menu")
    )
    
    bot.send_message(
        message.chat.id,
        config_text,
        reply_markup=keyboard
    )

@bot.message_handler(commands=['start_spam'])
@user_access_required
def start_spam_command(message: Message):
    """Start continuous spam"""
    global spam_active, spam_thread
    
    user_id = message.from_user.id
    
    # Check if already running
    if spam_active:
        bot.send_message(message.chat.id, "⚠️ <b>Spam is already running!</b>")
        return
    
    # Check requirements
    if not data_manager.messages:
        bot.send_message(message.chat.id,
            "❌ <b>No messages found!</b>\n\n"
            "Add messages first using /addmsg"
        )
        return
    
    valid_sessions = data_manager.get_valid_sessions()
    if not valid_sessions:
        bot.send_message(message.chat.id,
            "❌ <b>No valid sessions found!</b>\n\n"
            "Add Instagram sessions first using /addsession"
        )
        return
    
    dm_url = data_manager.settings.get('dm_url', '')
    if not dm_url:
        bot.send_message(message.chat.id,
            "❌ <b>No Instagram URL set!</b>\n\n"
            "Set the target URL first using /setup"
        )
        return
    
    thread_id = extract_thread_id(dm_url)
    if not thread_id:
        bot.send_message(message.chat.id,
            "❌ <b>Invalid URL format!</b>\n\n"
            "<b>Correct formats:</b>\n"
            "• https://www.instagram.com/direct/t/THREAD_ID/\n"
            "• Direct thread ID: 17850716417587515\n"
            "• Instagram DM link\n\n"
            "Use /setup to set the correct URL"
        )
        return
    
    # Start spam
    spam_active = True
    
    # Start spam thread
    spam_thread = threading.Thread(
        target=spam_worker,
        args=(message.chat.id, thread_id, user_id),
        daemon=True
    )
    spam_thread.start()
    
    # Get settings
    settings = data_manager.settings
    mode_text = "♾️ CONTINUOUS MODE" if settings.get('continuous_mode', True) else "📊 LIMITED MODE"
    
    bot.send_message(
        message.chat.id,
        f"🚀 <b>SPAM STARTED SUCCESSFULLY!</b>\n\n"
        f"{mode_text}\n\n"
        f"🎯 <b>Target:</b> {settings.get('target', 'N/A')}\n"
        f"🔗 <b>Thread ID:</b> <code>{thread_id}</code>\n"
        f"📊 <b>Messages:</b> {len(data_manager.messages)}\n"
        f"👥 <b>Sessions:</b> {len(valid_sessions)}\n"
        f"⏱️ <b>Delay:</b> {settings.get('delay_min', 2)}-{settings.get('delay_max', 5)}s\n\n"
        f"<i>Spam will continue until you stop it with /stop_spam</i>\n"
        f"<i>Check progress with /stats</i>"
    )

@bot.message_handler(commands=['stop_spam'])
@user_access_required
def stop_spam_command(message: Message):
    """Stop spam"""
    global spam_active
    
    if not spam_active:
        bot.send_message(message.chat.id, "⚠️ <b>No spam is currently running!</b>")
        return
    
    spam_active = False
    bot.send_message(
        message.chat.id,
        "🛑 <b>Stopping spam...</b>\n\n"
        "<i>Current operation will finish, then spam will stop completely.</i>\n"
        "<i>This may take a few seconds...</i>"
    )

@bot.message_handler(commands=['stats'])
@user_access_required
def stats_command(message: Message):
    """Show statistics"""
    user_id = message.from_user.id
    is_admin = data_manager.is_admin(user_id)
    
    # Get stats
    valid_sessions = len(data_manager.get_valid_sessions())
    active_users = len(data_manager.get_active_users())
    settings = data_manager.settings
    
    total = success_count + fail_count
    success_rate = (success_count / total * 100) if total > 0 else 0
    
    stats_text = f"""
📊 <b>BOT STATISTICS</b>

📈 <b>PERFORMANCE:</b>
✅ Successful Messages: {success_count}
❌ Failed Messages: {fail_count}
📈 Success Rate: {success_rate:.1f}%

📦 <b>RESOURCES:</b>
💬 Messages Available: {len(data_manager.messages)}
👥 Valid Sessions: {valid_sessions}/{len(data_manager.sessions)}
👤 Active Users: {active_users}/{len(data_manager.users)}

🎯 <b>TARGET SETTINGS:</b>
Target: {settings.get('target', 'Not set')}
URL Set: {'✅ Yes' if settings.get('dm_url') else '❌ No'}

⚙️ <b>CONFIGURATION:</b>
Delay: {settings.get('delay_min', 2)}-{settings.get('delay_max', 5)}s
Mode: {'CONTINUOUS' if settings.get('continuous_mode', True) else 'LIMITED'}

📤 <b>ACTIVITY:</b>
Total Messages Sent: {settings.get('messages_sent', 0)}
Spam Status: {'🟢 RUNNING' if spam_active else '🔴 STOPPED'}
"""
    
    if is_admin:
        # Add admin stats
        stats_text += f"""
🔐 <b>ADMIN STATS:</b>
Total Users: {len(data_manager.users)}
User Growth: {len(data_manager.get_active_users())} active
Backups Created: {len(list(BACKUP_DIR.glob('*')))}
"""
    
    bot.send_message(message.chat.id, stats_text)

@bot.message_handler(commands=['users'])
@admin_required
def users_command(message: Message):
    """View all users (Admin only)"""
    users = data_manager.get_all_users()
    
    if not users:
        bot.send_message(message.chat.id, "📭 <b>No users found!</b>")
        return
    
    response = f"👥 <b>TOTAL USERS: {len(users)}</b>\n\n"
    
    # Show users in pages
    page = 0
    users_per_page = 10
    
    # Calculate pages
    total_pages = (len(users) + users_per_page - 1) // users_per_page
    
    # Get page from callback or default to 0
    try:
        if ' ' in message.text:
            page = int(message.text.split()[1]) - 1
    except:
        page = 0
    
    page = max(0, min(page, total_pages - 1))
    
    start_idx = page * users_per_page
    end_idx = start_idx + users_per_page
    
    for i, user in enumerate(users[start_idx:end_idx], start_idx + 1):
        status = "🛡️ ADMIN" if user.is_admin else "👤 USER"
        active = "✅ Active" if user.active else "❌ Inactive"
        expiry = user.expiry.strftime("%Y-%m-%d")
        
        response += f"{status} - {active}\n"
        response += f"ID: <code>{user.id}</code>\n"
        response += f"Username: {user.username}\n"
        response += f"Plan: {user.plan}\n"
        response += f"Expires: {expiry}\n"
        response += f"Messages: {user.message_count}\n"
        response += "─" * 30 + "\n\n"
    
    response += f"📄 <b>Page {page + 1}/{total_pages}</b>"
    
    # Create pagination keyboard
    keyboard = InlineKeyboardMarkup(row_width=3)
    
    if page > 0:
        keyboard.add(InlineKeyboardButton("◀️ Previous", callback_data=f"users_page_{page-1}"))
    
    keyboard.add(InlineKeyboardButton(f"{page+1}/{total_pages}", callback_data="users_current"))
    
    if page < total_pages - 1:
        keyboard.add(InlineKeyboardButton("Next ▶️", callback_data=f"users_page_{page+1}"))
    
    keyboard.add(
        InlineKeyboardButton("🔄 Refresh", callback_data="users_refresh"),
        InlineKeyboardButton("📋 Export", callback_data="users_export"),
        InlineKeyboardButton("◀️ Admin Panel", callback_data="admin_panel")
    )
    
    bot.send_message(
        message.chat.id,
        response,
        reply_markup=keyboard
    )

@bot.message_handler(commands=['broadcast'])
@admin_required
def broadcast_command(message: Message):
    """Broadcast message to all users (Admin only)"""
    bot.send_message(
        message.chat.id,
        "📢 <b>SEND BROADCAST MESSAGE</b>\n\n"
        "Send the message you want to broadcast to all users:\n\n"
        "⚠️ <i>This will be sent to ALL registered users</i>"
    )
    
    bot.set_state(message.from_user.id, BotStates.admin_broadcast, message.chat.id)

@bot.message_handler(state=BotStates.admin_broadcast)
def process_broadcast(message: Message):
    """Process broadcast message"""
    user_id = message.from_user.id
    
    with bot.retrieve_data(user_id, message.chat.id) as data:
        pass
    
    broadcast_text = message.text.strip()
    
    if not broadcast_text:
        bot.send_message(message.chat.id, "❌ Message cannot be empty!")
        bot.delete_state(user_id, message.chat.id)
        return
    
    # Get active users
    active_users = data_manager.get_active_users()
    
    if not active_users:
        bot.send_message(message.chat.id, "❌ No active users found!")
        bot.delete_state(user_id, message.chat.id)
        return
    
    bot.send_message(message.chat.id, f"📤 <b>Broadcasting to {len(active_users)} users...</b>")
    
    sent = 0
    failed = 0
    
    for user in active_users:
        try:
            bot.send_message(
                user.id,
                f"📢 <b>ANNOUNCEMENT FROM ADMIN</b>\n\n"
                f"{broadcast_text}\n\n"
                f"<i>Sent via {BOT_USERNAME}</i>"
            )
            sent += 1
            time.sleep(0.1)  # Rate limiting
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user.id}: {e}")
            failed += 1
    
    bot.send_message(
        message.chat.id,
        f"✅ <b>BROADCAST COMPLETE!</b>\n\n"
        f"✅ Successfully sent: {sent}\n"
        f"❌ Failed: {failed}\n"
        f"📊 Total users: {len(active_users)}\n\n"
        f"<i>Message preview: {broadcast_text[:100]}...</i>"
    )
    
    bot.delete_state(user_id, message.chat.id)

@bot.message_handler(commands=['addtime'])
@admin_required
def addtime_command(message: Message):
    """Add time to user account (Admin only)"""
    bot.send_message(
        message.chat.id,
        "⏰ <b>ADD TIME TO USER</b>\n\n"
        "Send in format:\n"
        "<code>user_id amount unit</code>\n\n"
        "<b>Examples:</b>\n"
        "<code>123456789 7 days</code>\n"
        "<code>123456789 1 lifetime</code>\n\n"
        "<b>Available units:</b>\n"
        "• minutes - Add minutes\n"
        "• hours - Add hours\n"
        "• days - Add days\n"
        "• weeks - Add weeks\n"
        "• months - Add months\n"
        "• lifetime - Lifetime access\n\n"
        "<i>User will be notified automatically</i>"
    )
    
    bot.set_state(message.from_user.id, BotStates.add_time_user, message.chat.id)

@bot.message_handler(state=BotStates.add_time_user)
def process_addtime(message: Message):
    """Process add time command"""
    user_id = message.from_user.id
    
    with bot.retrieve_data(user_id, message.chat.id) as data:
        pass
    
    text = message.text.strip()
    parts = text.split()
    
    if len(parts) < 3:
        bot.send_message(message.chat.id,
            "❌ <b>Invalid format!</b>\n\n"
            "Use: <code>user_id amount unit</code>\n"
            "Example: <code>123456789 30 days</code>"
        )
        bot.delete_state(user_id, message.chat.id)
        return
    
    try:
        target_user_id = int(parts[0])
        amount = int(parts[1])
        unit = parts[2].lower()
        
        valid_units = ["minutes", "hours", "days", "weeks", "months", "lifetime"]
        
        if unit not in valid_units:
            bot.send_message(message.chat.id,
                f"❌ <b>Invalid unit!</b>\n\n"
                f"Valid units: {', '.join(valid_units)}"
            )
            bot.delete_state(user_id, message.chat.id)
            return
        
        # Add time
        success = data_manager.add_time_to_user(target_user_id, amount, unit)
        
        if success:
            # Notify admin
            if unit == "lifetime":
                time_msg = "LIFETIME access"
            else:
                time_msg = f"{amount} {unit}"
            
            bot.send_message(
                message.chat.id,
                f"✅ <b>TIME ADDED SUCCESSFULLY!</b>\n\n"
                f"👤 User ID: <code>{target_user_id}</code>\n"
                f"⏰ Added: {time_msg}\n"
                f"✅ User has been notified"
            )
            
            # Try to notify user
            try:
                user = data_manager.get_user(target_user_id)
                if user:
                    bot.send_message(
                        target_user_id,
                        f"🎉 <b>ACCOUNT UPDATED!</b>\n\n"
                        f"Admin has added {time_msg} to your account.\n"
                        f"Your access has been extended!\n\n"
                        f"<i>Thank you for using our service! 🚀</i>"
                    )
            except:
                pass
        else:
            bot.send_message(message.chat.id,
                "❌ <b>User not found!</b>\n"
                "Make sure the user ID is correct."
            )
    
    except ValueError:
        bot.send_message(message.chat.id, "❌ <b>Invalid user ID or amount!</b>")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ <b>Error:</b> {str(e)}")
    
    bot.delete_state(user_id, message.chat.id)

@bot.message_handler(commands=['backup'])
@admin_required
def backup_command(message: Message):
    """Create backup of all data (Admin only)"""
    bot.send_message(message.chat.id, "💾 <b>Creating backup...</b>")
    
    success = data_manager.backup_data()
    
    if success:
        # Count backups
        backup_count = len(list(BACKUP_DIR.glob('*')))
        
        bot.send_message(
            message.chat.id,
            f"✅ <b>BACKUP CREATED SUCCESSFULLY!</b>\n\n"
            f"📁 Total backups: {backup_count}\n"
            f"🕒 Time: {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"<i>Backups are stored in: {BACKUP_DIR}</i>"
        )
    else:
        bot.send_message(
            message.chat.id,
            "❌ <b>BACKUP FAILED!</b>\n\n"
            "Check logs for details."
        )

# ========== CALLBACK HANDLERS ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call: CallbackQuery):
    """Handle all inline keyboard callbacks"""
    user_id = call.from_user.id
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    logger.info(f"Callback from {user_id}: {call.data}")
    
    # Check access
    if not data_manager.is_admin(user_id):
        has_access, access_msg = data_manager.check_user_access(user_id)
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
        start_command(call.message)
    
    elif call.data == "admin_panel":
        admin_command(call.message)
    
    elif call.data == "admin_users":
        users_command(call.message)
    
    elif call.data == "admin_stats":
        stats_command(call.message)
    
    elif call.data == "admin_broadcast":
        broadcast_command(call.message)
    
    elif call.data == "admin_addtime":
        addtime_command(call.message)
    
    elif call.data == "admin_backup":
        backup_command(call.message)
    
    elif call.data == "admin_refresh":
        data_manager.save_all_data()
        bot.answer_callback_query(call.id, "✅ Data refreshed!", show_alert=True)
        admin_command(call.message)
    
    elif call.data == "add_msg":
        bot.delete_message(chat_id, message_id)
        addmsg_command(call.message)
    
    elif call.data == "list_msg":
        bot.delete_message(chat_id, message_id)
        listmsg_command(call.message)
    
    elif call.data == "add_session":
        bot.delete_message(chat_id, message_id)
        addsession_command(call.message)
    
    elif call.data == "list_sessions":
        bot.delete_message(chat_id, message_id)
        sessions_command(call.message)
    
    elif call.data == "setup":
        bot.delete_message(chat_id, message_id)
        setup_command(call.message)
    
    elif call.data == "start_spam":
        bot.delete_message(chat_id, message_id)
        start_spam_command(call.message)
    
    elif call.data == "stop_spam":
        bot.delete_message(chat_id, message_id)
        stop_spam_command(call.message)
    
    elif call.data == "stats":
        bot.delete_message(chat_id, message_id)
        stats_command(call.message)
    
    elif call.data.startswith("delete_msg_"):
        message_id_to_delete = call.data.replace("delete_msg_", "")
        if data_manager.delete_message(message_id_to_delete):
            bot.answer_callback_query(call.id, "✅ Message deleted!", show_alert=True)
            listmsg_command(call.message)
        else:
            bot.answer_callback_query(call.id, "❌ Message not found!", show_alert=True)
    
    elif call.data == "set_target":
        bot.send_message(chat_id, "🎯 <b>Enter target username:</b>")
        bot.set_state(user_id, BotStates.set_target, chat_id)
    
    elif call.data == "set_url":
        bot.send_message(chat_id,
            "🔗 <b>Enter Instagram URL:</b>\n\n"
            "<b>Supported formats:</b>\n"
            "• Full URL: https://www.instagram.com/direct/t/THREAD_ID/\n"
            "• Thread ID only: 17850716417587515\n"
            "• DM link from Instagram app"
        )
        bot.set_state(user_id, BotStates.set_url, chat_id)
    
    elif call.data == "set_delay":
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        keyboard.add(
            InlineKeyboardButton("⚡ 1-2s (Very Fast)", callback_data="delay_1_2"),
            InlineKeyboardButton("🚀 2-3s (Fast)", callback_data="delay_2_3"),
            InlineKeyboardButton("🐇 3-5s (Normal)", callback_data="delay_3_5"),
            InlineKeyboardButton("🐢 5-10s (Safe)", callback_data="delay_5_10"),
            InlineKeyboardButton("⏳ 10-20s (Very Safe)", callback_data="delay_10_20"),
            InlineKeyboardButton("🔙 Back", callback_data="setup")
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
            data_manager.settings["delay_min"] = int(delays[0])
            data_manager.settings["delay_max"] = int(delays[1])
            data_manager.save_all_data()
            
            bot.answer_callback_query(
                call.id,
                f"✅ Delay set to {delays[0]}-{delays[1]} seconds",
                show_alert=True
            )
            
            setup_command(call.message)
    
    elif call.data == "toggle_mode":
        current_mode = data_manager.settings.get("continuous_mode", True)
        data_manager.settings["continuous_mode"] = not current_mode
        data_manager.save_all_data()
        
        mode_text = "CONTINUOUS" if not current_mode else "LIMITED"
        bot.answer_callback_query(call.id, f"✅ Mode changed to {mode_text}", show_alert=True)
        
        setup_command(call.message)
    
    elif call.data.startswith("users_page_"):
        page = int(call.data.split("_")[2])
        msg = type('obj', (object,), {
            'text': f'/users {page + 1}',
            'chat': type('obj', (object,), {'id': chat_id}),
            'from_user': type('obj', (object,), {'id': user_id})
        })
        users_command(msg)

@bot.message_handler(state=BotStates.set_target)
def process_set_target(message: Message):
    """Process target setting"""
    user_id = message.from_user.id
    
    target = message.text.strip()
    if target:
        data_manager.settings["target"] = target
        data_manager.save_all_data()
        
        bot.send_message(
            message.chat.id,
            f"✅ <b>Target set to:</b> {target}"
        )
    else:
        bot.send_message(message.chat.id, "❌ Target cannot be empty!")
    
    bot.delete_state(user_id, message.chat.id)
    setup_command(message)

@bot.message_handler(state=BotStates.set_url)
def process_set_url(message: Message):
    """Process URL setting"""
    user_id = message.from_user.id
    
    url = message.text.strip()
    if not url:
        bot.send_message(message.chat.id, "❌ URL cannot be empty!")
        bot.delete_state(user_id, message.chat.id)
        return
    
    thread_id = extract_thread_id(url)
    
    data_manager.settings["dm_url"] = url
    data_manager.save_all_data()
    
    if thread_id:
        bot.send_message(
            message.chat.id,
            f"✅ <b>URL SET SUCCESSFULLY!</b>\n\n"
            f"🔗 Thread ID: <code>{thread_id}</code>\n"
            f"📝 URL: {url[:50]}..."
        )
    else:
        bot.send_message(
            message.chat.id,
            "⚠️ <b>URL SAVED BUT THREAD ID NOT DETECTED</b>\n\n"
            "Make sure the URL is correct:\n"
            "• https://www.instagram.com/direct/t/THREAD_ID/\n"
            "• Or provide thread ID directly"
        )
    
    bot.delete_state(user_id, message.chat.id)
    setup_command(message)

# ========== ERROR HANDLER ==========
@bot.message_handler(func=lambda message: True)
def handle_other_messages(message: Message):
    """Handle other messages"""
    user_id = message.from_user.id
    
    # Check if it's a command we don't handle
    if message.text and message.text.startswith('/'):
        bot.send_message(
            message.chat.id,
            "❌ <b>Unknown command!</b>\n\n"
            "Use /start to see available commands."
        )
    else:
        # Auto-register user if they send any message
        username = message.from_user.username or message.from_user.first_name or f"user_{user_id}"
        data_manager.add_user(user_id, username)
        
        bot.send_message(
            message.chat.id,
            "👋 <b>Welcome!</b>\n\n"
            "I've registered you in the system.\n"
            "Use /start to see all available commands."
        )

# ========== MAIN FUNCTION ==========
def main():
    """Main function to start the bot"""
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║     INSTAGRAM SPAM BOT v4.0 - ADMIN EDITION             ║
║     FULLY FIXED & ENHANCED                              ║
║     GITHUB: https://github.com/M0bsyy/M0bsy-spam-bot.git║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Display admin info
    print(f"🔑 ADMIN USER IDs: {ADMIN_USER_IDS}")
    print(f"🤖 BOT USERNAME: {BOT_USERNAME}")
    print(f"📞 CONTACT: {CONTACT_USERNAME}")
    print(f"\n📊 LOADED DATA:")
    print(f"   • Users: {len(data_manager.users)}")
    print(f"   • Messages: {len(data_manager.messages)}")
    print(f"   • Sessions: {len(data_manager.sessions)}")
    print(f"   • Valid Sessions: {len(data_manager.get_valid_sessions())}")
    
    try:
        # Get bot info
        bot_info = bot.get_me()
        print(f"\n✅ BOT STARTED SUCCESSFULLY!")
        print(f"✅ Bot: @{bot_info.username}")
        print(f"✅ Bot ID: {bot_info.id}")
        print(f"✅ Bot Name: {bot_info.first_name}")
        print(f"✅ Parse Mode: HTML")
    except Exception as e:
        print(f"\n❌ ERROR STARTING BOT: {e}")
        logger.error(f"Bot start error: {e}")
        return
    
    print(f"\n{'='*60}")
    print("📋 ADMIN COMMANDS AVAILABLE:")
    print(f"   • /admin - Admin control panel")
    print(f"   • /users - View all users")
    print(f"   • /broadcast - Send message to all users")
    print(f"   • /addtime - Add time to user account")
    print(f"   • /backup - Create data backup")
    print(f"{'='*60}")
    print("📋 USER COMMANDS AVAILABLE:")
    print(f"   • /start - Main menu")
    print(f"   • /addmsg - Add spam message")
    print(f"   • /addsession - Add Instagram session")
    print(f"   • /setup - Configure spam")
    print(f"   • /start_spam - Start spam")
    print(f"   • /stop_spam - Stop spam")
    print(f"{'='*60}")
    print("🚀 Bot is now running...")
    print("Press Ctrl+C to stop")
    print(f"{'='*60}\n")
    
    # Start bot
    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        logger.error(f"Bot polling error: {e}")
        print(f"❌ Bot polling error: {e}")
    finally:
        # Save data before exit
        data_manager.save_all_data()
        print("\n🛑 Bot stopped. Data saved.")

if __name__ == "__main__":
    # Run the bot
    main()
