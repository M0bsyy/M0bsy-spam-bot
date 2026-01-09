import os
import sys
import json
import random
import time
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import requests
from bs4 import BeautifulSoup
import aiohttp

# ========== CONFIGURATION ==========
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
ADMIN_USER_ID = "YOUR_USER_ID_HERE"

# Initialize bot and dispatcher
bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# ========== USER & PAYMENT MANAGEMENT ==========
class UserManager:
    def __init__(self):
        self.users_file = Path("users_data.json")
        self.users = self.load_users()
        
    def load_users(self) -> Dict:
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
                "plan": "free",
                "expiry": (datetime.now() + timedelta(days=30)).isoformat(),  # 30 DAYS FREE FOR ALL
                "joined": datetime.now().isoformat(),
                "active": True,
                "is_admin": False,
                "created_by": "system"
            }
            self.save_users()
            return True
        return False
    
    def grant_access(self, user_id: str, duration_type: str, value: int, granted_by: str):
        duration_map = {
            "minutes": timedelta(minutes=value),
            "hours": timedelta(hours=value),
            "days": timedelta(days=value),
            "weeks": timedelta(weeks=value),
            "months": timedelta(days=value*30),
            "permanent": timedelta(days=365*100)
        }
        
        if duration_type in duration_map:
            expiry = datetime.now() + duration_map[duration_type]
            plan = f"paid_{duration_type}_{value}"
        else:
            expiry = datetime.now() + timedelta(days=30)  # Default 30 days
            plan = "free"
        
        if str(user_id) not in self.users:
            self.add_user(user_id)
        
        self.users[str(user_id)].update({
            "plan": plan,
            "expiry": expiry.isoformat(),
            "active": True,
            "granted_by": granted_by,
            "granted_at": datetime.now().isoformat()
        })
        self.save_users()
        return True
    
    def revoke_access(self, user_id: str):
        if str(user_id) in self.users:
            self.users[str(user_id)]["active"] = False
            self.users[str(user_id)]["expiry"] = datetime.now().isoformat()
            self.save_users()
            return True
        return False
    
    def check_access(self, user_id: str) -> bool:
        user_data = self.users.get(str(user_id))
        if not user_data:
            return False
        
        if user_data.get("is_admin", False):
            return True
        
        expiry = datetime.fromisoformat(user_data.get("expiry", "2000-01-01"))
        if datetime.now() > expiry:
            user_data["active"] = False
            self.save_users()
            return False
        
        return user_data.get("active", False)
    
    def is_admin(self, user_id: str) -> bool:
        user_data = self.users.get(str(user_id))
        return user_data.get("is_admin", False) if user_data else False
    
    def make_admin(self, user_id: str, by_admin: str):
        if str(user_id) not in self.users:
            self.add_user(user_id)
        
        self.users[str(user_id)].update({
            "is_admin": True,
            "admin_since": datetime.now().isoformat(),
            "made_by": by_admin
        })
        self.save_users()
        return True
    
    def remove_admin(self, user_id: str):
        if str(user_id) in self.users:
            self.users[str(user_id)]["is_admin"] = False
            self.save_users()
            return True
        return False
    
    def get_all_users(self) -> List[Dict]:
        return [{"id": uid, **data} for uid, data in self.users.items()]
    
    def get_active_users(self) -> List[Dict]:
        active_users = []
        for uid, data in self.users.items():
            if self.check_access(uid):
                active_users.append({"id": uid, **data})
        return active_users
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        if str(user_id) in self.users:
            user_data = self.users[str(user_id)].copy()
            expiry = datetime.fromisoformat(user_data.get("expiry", "2000-01-01"))
            user_data["expiry_str"] = expiry.strftime("%Y-%m-%d %H:%M:%S")
            user_data["is_expired"] = datetime.now() > expiry
            user_data["days_left"] = (expiry - datetime.now()).days
            return user_data
        return None
    
    def get_expiry(self, user_id: str) -> str:
        user_info = self.get_user_info(user_id)
        if user_info and "expiry_str" in user_info:
            return user_info["expiry_str"]
        return "No active subscription"

# ========== BROADCAST SYSTEM ==========
class BroadcastManager:
    def __init__(self, user_manager: UserManager):
        self.user_manager = user_manager
        self.broadcast_logs = []
        
    async def broadcast_message(self, bot: Bot, message: Message, text: str):
        active_users = self.user_manager.get_active_users()
        total = len(active_users)
        successful = 0
        failed = 0
        
        status_msg = await message.answer(f"📢 Starting broadcast to {total} users...")
        
        for user in active_users:
            try:
                await bot.send_message(
                    chat_id=int(user["id"]),
                    text=text,
                    parse_mode=ParseMode.MARKDOWN
                )
                successful += 1
                
                if successful % 10 == 0:
                    await status_msg.edit_text(
                        f"📢 Broadcasting...\n"
                        f"✅ Successful: {successful}/{total}\n"
                        f"❌ Failed: {failed}"
                    )
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                failed += 1
                logging.error(f"Failed to send to {user['id']}: {e}")
        
        self.broadcast_logs.append({
            "time": datetime.now().isoformat(),
            "sent_by": message.from_user.id,
            "total": total,
            "successful": successful,
            "failed": failed,
            "message": text[:100] + "..." if len(text) > 100 else text
        })
        
        await status_msg.edit_text(
            f"📢 Broadcast Complete!\n\n"
            f"✅ Successful: {successful}\n"
            f"❌ Failed: {failed}\n"
            f"📊 Total: {total}\n\n"
            f"⏱️ Time: {datetime.now().strftime('%H:%M:%S')}"
        )

# ========== SPAM BOT GLOBAL VARIABLES ==========
spam_active = False
spam_threads = []
success_count = 0
unsuccess_count = 0
counter_lock = threading.Lock()
custom_messages = []
instagram_sessions = []
current_settings = {
    "target": "",
    "delay_min": 2,
    "delay_max": 5,
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
        logging.error(f"Error saving messages: {e}")

def load_messages():
    global custom_messages
    try:
        if MESSAGES_FILE.exists():
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                custom_messages = json.load(f)
    except Exception as e:
        logging.error(f"Error loading messages: {e}")
        custom_messages = []

def save_sessions():
    try:
        with open(SESSIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(instagram_sessions, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Error saving sessions: {e}")

def load_sessions():
    global instagram_sessions
    try:
        if SESSIONS_FILE.exists():
            with open(SESSIONS_FILE, 'r', encoding='utf-8') as f:
                instagram_sessions = json.load(f)
    except Exception as e:
        logging.error(f"Error loading sessions: {e}")
        instagram_sessions = []

# Load data on startup
load_messages()
load_sessions()

# ========== INSTAGRAM SESSION HANDLER ==========
class InstagramSession:
    def __init__(self, session_id, username=""):
        self.session_id = session_id
        self.username = username
        self.status = "inactive"
        self.last_used = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
        self.cookies = {
            'sessionid': session_id
        }

    async def verify_session(self):
        try:
            url = "https://www.instagram.com/accounts/edit/"
            async with aiohttp.ClientSession(cookies=self.cookies) as session:
                async with session.get(url, headers=self.headers, timeout=10) as response:
                    if response.status == 200:
                        text = await response.text()
                        if 'username' in text:
                            soup = BeautifulSoup(text, 'html.parser')
                            meta = soup.find('meta', property='og:title')
                            if meta and meta.get('content'):
                                self.username = meta['content'].split('(')[0].strip()
                            self.status = "active"
                            self.last_used = datetime.now().isoformat()
                            return True
            self.status = "invalid"
            return False
        except Exception as e:
            logging.error(f"Error verifying session: {e}")
            self.status = "error"
            return False

# ========== INITIALIZE MANAGERS ==========
user_manager = UserManager()
broadcast_manager = BroadcastManager(user_manager)

# ========== ALL STATES ==========
class Form(StatesGroup):
    # Admin states
    waiting_for_grant_user = State()
    waiting_for_grant_duration = State()
    waiting_for_grant_value = State()
    waiting_for_broadcast = State()
    waiting_for_revoke_user = State()
    waiting_for_make_admin = State()
    
    # Spam bot states
    waiting_for_target = State()
    waiting_for_message = State()
    waiting_for_session = State()
    waiting_for_url = State()
    waiting_for_delay_min = State()
    waiting_for_delay_max = State()
    waiting_for_count = State()
    editing_message = State()
    adding_session = State()
    editing_session = State()

# ========== HELPER FUNCTIONS ==========
def print_banner():
    banner = """
╔════════════════════════════════════════════╗
║        INSTAGRAM SPAM BOT v3.0             ║
║      (Complete System with Admin Panel)    ║
╚════════════════════════════════════════════╝
    """
    return banner

async def send_start_message(message: Message):
    """Show main help message with all commands"""
    user_id = str(message.from_user.id)
    is_admin = user_manager.is_admin(user_id)
    
    welcome_text = f"""
{print_banner()}

📋 *Available Commands:*

🔹 /start - Show this help message
🔹 /addmsg - Add a new message for spamming
🔹 /listmsg - List all saved messages
🔹 /delsession - Delete a session
🔹 /editsession - Edit a session
🔹 /setup - Configure spam settings
🔹 /sessions - View/Manage Instagram sessions
🔹 /addsession - Add new Instagram session
🔹 /start_spam - Begin sending messages
🔹 /stop_spam - Stop sending messages
🔹 /stats - Show current statistics
🔹 /reset - Reset all counters

{"🔹 /admin - Admin Panel (Admin Only)" if is_admin else ""}

📊 *Current Status:*
• Messages saved: {len(custom_messages)}
• Sessions active: {len([s for s in instagram_sessions if s.get('status') == 'active'])}/{len(instagram_sessions)}
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
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    await message.answer(welcome_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

# ========== ORIGINAL SPAM BOT COMMANDS ==========
@dp.message(CommandStart())
async def start_command(message: Message):
    """Handle /start command"""
    user_id = str(message.from_user.id)
    username = message.from_user.username or message.from_user.first_name
    
    # Add user if not exists
    user_manager.add_user(user_id, username)
    
    # Make configured user admin
    if user_id == ADMIN_USER_ID:
        user_manager.make_admin(user_id, "system")
    
    # ⭐⭐⭐ EVERYONE GETS 30 DAYS ACCESS AUTOMATICALLY ⭐⭐⭐
    if not user_manager.check_access(user_id):
        # Grant 30 days access automatically to everyone
        user_manager.grant_access(
            user_id=user_id,
            duration_type="days",
            value=30,
            granted_by="auto_grant"
        )
    
    await send_start_message(message)

@dp.message(Command("addmsg"))
async def addmsg_command(message: Message, state: FSMContext):
    """Add a new message for spamming"""
    user_id = str(message.from_user.id)
    # ⭐⭐⭐ REMOVED ACCESS CHECK - EVERYONE CAN USE ⭐⭐⭐
    
    await message.answer("✍️ Please send the message you want to add for spamming.\n\nYou can use {target} as a placeholder for the target name:")
    await state.set_state(Form.waiting_for_message)

@dp.message(Form.waiting_for_message)
async def process_new_message(message: Message, state: FSMContext):
    new_message = message.text
    custom_messages.append(new_message)
    save_messages()
    
    await message.answer(f"✅ Message added successfully!\n\nTotal messages: {len(custom_messages)}\n\n📝 Preview:\n{new_message[:200]}")
    await state.clear()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Another", callback_data="add_msg"),
         InlineKeyboardButton(text="📋 View All", callback_data="list_msg")],
        [InlineKeyboardButton(text="⚙️ Setup Spam", callback_data="setup")]
    ])
    await message.answer("What would you like to do next?", reply_markup=keyboard)

@dp.message(Command("listmsg"))
async def listmsg_command(message: Message):
    """List all saved messages"""
    # ⭐⭐⭐ REMOVED ACCESS CHECK - EVERYONE CAN USE ⭐⭐⭐
    
    if not custom_messages:
        await message.answer("📭 No messages saved yet. Use /addmsg to add messages.")
        return
    
    response = "📋 *Saved Messages:*\n\n"
    for i, msg in enumerate(custom_messages, 1):
        preview = msg[:50] + "..." if len(msg) > 50 else msg
        response += f"{i}. `{preview}`\n"
    
    response += f"\nTotal: {len(custom_messages)} messages"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Delete", callback_data="delete_msg_menu"),
         InlineKeyboardButton(text="✏️ Edit", callback_data="edit_msg_menu")],
        [InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")]
    ])
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@dp.message(Command("addsession"))
async def addsession_command(message: Message, state: FSMContext):
    """Add new Instagram session"""
    # ⭐⭐⭐ REMOVED ACCESS CHECK - EVERYONE CAN USE ⭐⭐⭐
    
    await message.answer("🔑 Please send your Instagram session ID:\n\nTo get session ID:\n1. Login to Instagram in Chrome\n2. Press F12 → Application tab\n3. Find Cookies → https://instagram.com\n4. Copy 'sessionid' value")
    await state.set_state(Form.adding_session)

@dp.message(Form.adding_session)
async def process_new_session(message: Message, state: FSMContext):
    session_id = message.text.strip()
    
    # Create session object
    session_obj = InstagramSession(session_id)
    
    await message.answer("🔍 Verifying session ID...")
    
    # Verify session
    is_valid = await session_obj.verify_session()
    
    if is_valid:
        # Save session
        session_data = {
            "session_id": session_id,
            "username": session_obj.username,
            "status": session_obj.status,
            "last_used": session_obj.last_used,
            "added_on": datetime.now().isoformat()
        }
        instagram_sessions.append(session_data)
        save_sessions()
        
        await message.answer(f"""
✅ Session added successfully!

👤 Username: {session_obj.username or 'Unknown'}
🔑 Status: {session_obj.status}
📅 Added: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Total sessions: {len(instagram_sessions)}
        """)
    else:
        await message.answer(f"""
❌ Invalid session ID!

The session ID could not be verified. Please check:
1. Make sure you're copying the entire sessionid value
2. Try logging in again and get a fresh session ID
3. The account should not have 2FA enabled for this method
        """)
    
    await state.clear()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Another", callback_data="add_session"),
         InlineKeyboardButton(text="👥 View Sessions", callback_data="list_sessions")],
        [InlineKeyboardButton(text="⚙️ Setup Spam", callback_data="setup")]
    ])
    await message.answer("What would you like to do next?", reply_markup=keyboard)

@dp.message(Command("sessions"))
async def sessions_command(message: Message):
    """View/Manage Instagram sessions"""
    # ⭐⭐⭐ REMOVED ACCESS CHECK - EVERYONE CAN USE ⭐⭐⭐
    
    await list_sessions_menu(message)

async def list_sessions_menu(message: Message):
    if not instagram_sessions:
        await message.answer("🔐 No Instagram sessions saved. Use /addsession to add one.")
        return
    
    response = "👥 *Instagram Sessions:*\n\n"
    active_count = 0
    
    for i, session in enumerate(instagram_sessions, 1):
        status_emoji = "🟢" if session.get('status') == 'active' else "🔴"
        username = session.get('username', 'Unknown')
        added = session.get('added_on', '').split('T')[0] if session.get('added_on') else 'Unknown'
        
        response += f"{i}. {status_emoji} `{username}`\n"
        response += f"   📅 Added: {added}\n"
        response += f"   🔑 Status: {session.get('status', 'unknown')}\n\n"
        
        if session.get('status') == 'active':
            active_count += 1
    
    response += f"\nActive: {active_count}/{len(instagram_sessions)}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Session", callback_data="add_session"),
         InlineKeyboardButton(text="🔄 Verify All", callback_data="verify_all")],
        [InlineKeyboardButton(text="❌ Delete Session", callback_data="delete_session_menu"),
         InlineKeyboardButton(text="✏️ Edit Session", callback_data="edit_session_menu")],
        [InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")]
    ])
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@dp.message(Command("setup"))
async def setup_command(message: Message):
    """Configure spam settings"""
    # ⭐⭐⭐ REMOVED ACCESS CHECK - EVERYONE CAN USE ⭐⭐⭐
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Set Target Name", callback_data="set_target"),
         InlineKeyboardButton(text="🔗 Set Group URL", callback_data="set_url")],
        [InlineKeyboardButton(text="⏱️ Set Delay", callback_data="set_delay"),
         InlineKeyboardButton(text="📊 Set Message Count", callback_data="set_count")],
        [InlineKeyboardButton(text="👥 Select Sessions", callback_data="select_sessions")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")]
    ])
    
    await message.answer("⚙️ *Setup Menu:*\n\nConfigure your spam settings:", 
                        parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@dp.message(Command("settings"))
async def settings_command(message: Message):
    """Show current settings"""
    # ⭐⭐⭐ REMOVED ACCESS CHECK - EVERYONE CAN USE ⭐⭐⭐
    
    active_sessions = current_settings.get('active_sessions', [])
    active_names = []
    for idx in active_sessions:
        if 0 <= idx < len(instagram_sessions):
            active_names.append(instagram_sessions[idx].get('username', f'Session {idx+1}'))
    
    settings_text = f"""
🔧 *Current Settings:*

🎯 Target: `{current_settings['target'] or 'Not set'}`
🔗 Group URL: `{current_settings['dm_url'][:50] + '...' if current_settings['dm_url'] and len(current_settings['dm_url']) > 50 else current_settings['dm_url'] or 'Not set'}`
⏱️ Delay: {current_settings['delay_min']} - {current_settings['delay_max']} seconds
📊 Message Count: {current_settings['message_count']}
👥 Active Sessions: {len(active_sessions)}/{len(instagram_sessions)}
{'   • ' + chr(10) + '   • '.join(active_names) if active_names else '   None selected'}
💬 Messages Saved: {len(custom_messages)}
"""
    await message.answer(settings_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("start_spam"))
async def start_spam_command(message: Message):
    """Begin sending messages"""
    # ⭐⭐⭐ REMOVED ACCESS CHECK - EVERYONE CAN USE ⭐⭐⭐
    
    if not current_settings['target']:
        await message.answer("❌ Please set target first using /setup")
        return
    
    if not current_settings['dm_url']:
        await message.answer("❌ Please set Group URL first using /setup")
        return
    
    if not custom_messages:
        await message.answer("❌ No messages to send! Use /addmsg to add messages.")
        return
    
    active_sessions = current_settings.get('active_sessions', [])
    if not active_sessions:
        await message.answer("❌ No sessions selected! Use /setup → 'Select Sessions' to choose which accounts to use.")
        return
    
    global spam_active, spam_threads
    
    if spam_active:
        await message.answer("⚠️ Spam is already running!")
        return
    
    # Start spam threads for each selected session
    spam_active = True
    spam_threads = []
    
    for session_idx in active_sessions:
        if 0 <= session_idx < len(instagram_sessions):
            thread = threading.Thread(
                target=spam_worker, 
                args=(message.chat.id, session_idx, len(spam_threads))
            )
            thread.daemon = True
            thread.start()
            spam_threads.append(thread)
    
    session_names = []
    for idx in active_sessions:
        if 0 <= idx < len(instagram_sessions):
            session_names.append(instagram_sessions[idx].get('username', f'Session {idx+1}'))
    
    await message.answer(f"""
✅ *Spam Started!*

🎯 Target: `{current_settings['target']}`
🔗 Group URL: `{current_settings['dm_url'][:50]}...`
📊 Messages: {len(custom_messages)} available
⏱️ Delay: {current_settings['delay_min']} - {current_settings['delay_max']} seconds
👥 Active Accounts: {len(active_sessions)}
{'   • ' + chr(10) + '   • '.join(session_names)}

📈 All selected accounts are now sending messages!

To stop, use /stop_spam
""", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("stop_spam"))
async def stop_spam_command(message: Message):
    """Stop sending messages"""
    # ⭐⭐⭐ REMOVED ACCESS CHECK - EVERYONE CAN USE ⭐⭐⭐
    
    global spam_active
    
    if not spam_active:
        await message.answer("⚠️ No active spam to stop!")
        return
    
    spam_active = False
    await message.answer("🛑 Spam stopped for all accounts!")

@dp.message(Command("stats"))
async def stats_command(message: Message):
    """Show current statistics"""
    # ⭐⭐⭐ REMOVED ACCESS CHECK - EVERYONE CAN USE ⭐⭐⭐
    
    active_sessions = current_settings.get('active_sessions', [])
    active_names = []
    for idx in active_sessions:
        if 0 <= idx < len(instagram_sessions):
            active_names.append(instagram_sessions[idx].get('username', f'Session {idx+1}'))
    
    stats_text = f"""
📊 *Current Statistics:*

✅ Successfully sent: {success_count}
❌ Failed: {unsuccess_count}
🎯 Target: {current_settings['target'] or 'Not set'}
🔗 Group URL: {current_settings['dm_url'][:30] + '...' if current_settings['dm_url'] and len(current_settings['dm_url']) > 30 else current_settings['dm_url'] or 'Not set'}
💬 Messages available: {len(custom_messages)}
👥 Active Accounts: {len(active_sessions)}
{'   • ' + chr(10) + '   • '.join(active_names) if active_names else '   None'}
📈 Spam Status: {'🟢 RUNNING' if spam_active else '🔴 STOPPED'}

👥 User Stats:
• Total Users: {len(user_manager.get_all_users())}
• Active Users: {len(user_manager.get_active_users())}

Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    await message.answer(stats_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("reset"))
async def reset_command(message: Message):
    """Reset all counters"""
    # ⭐⭐⭐ REMOVED ACCESS CHECK - EVERYONE CAN USE ⭐⭐⭐
    
    global success_count, unsuccess_count
    
    success_count = 0
    unsuccess_count = 0
    await message.answer("🔄 Statistics reset to zero!")

# ========== ADMIN COMMANDS ==========
@dp.message(Command("admin"))
async def admin_command(message: Message):
    """Admin panel"""
    user_id = str(message.from_user.id)
    if not user_manager.is_admin(user_id):
        await message.answer("❌ Admin access required!")
        return
    
    users = user_manager.get_all_users()
    active = user_manager.get_active_users()
    admins = [u for u in users if u.get("is_admin")]
    
    admin_text = f"""
🔐 *ADMIN PANEL*

👥 *User Management:*
/grant_access - Grant access to user
/revoke_access - Revoke user access
/make_admin - Make user admin
/remove_admin - Remove admin
/user_info [id] - Check user info
/list_users - List all users
/list_active - List active users

📢 *Broadcast:*
/broadcast - Send message to all users
/broadcast_stats - Show broadcast statistics

⚙️ *Bot Management:*
/stats - Bot statistics
/restart - Restart bot
/stop_spam - Stop all spam
/cleanup - Cleanup old data

📊 *Current Stats:*
Total Users: {len(users)}
Active Users: {len(active)}
Admins: {len(admins)}
Active Sessions: {len(instagram_sessions)}
"""
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 Grant Access", callback_data="admin_grant"),
         InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📊 User List", callback_data="admin_list_users"),
         InlineKeyboardButton(text="⚙️ Bot Stats", callback_data="admin_stats")],
        [InlineKeyboardButton(text="❌ Revoke Access", callback_data="admin_revoke"),
         InlineKeyboardButton(text="👑 Make Admin", callback_data="admin_make_admin")],
        [InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")]
    ])
    
    await message.answer(admin_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@dp.message(Command("grant_access"))
async def grant_access_command(message: Message, state: FSMContext):
    """Grant access to user"""
    user_id = str(message.from_user.id)
    if not user_manager.is_admin(user_id):
        await message.answer("❌ Admin access required!")
        return
    
    await message.answer(
        "👤 Send the user ID to grant access to:\n\n"
        "You can get user ID by forwarding their message to @userinfobot"
    )
    await state.set_state(Form.waiting_for_grant_user)

@dp.message(AdminStates.waiting_for_grant_user)
async def process_grant_user(message: Message, state: FSMContext):
    user_id = message.text.strip()
    
    if not user_id.isdigit():
        await message.answer("❌ Invalid user ID! Please send numeric ID only.")
        return
    
    await state.update_data(grant_user_id=user_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏱️ Minutes", callback_data="grant_minutes"),
         InlineKeyboardButton(text="🕐 Hours", callback_data="grant_hours")],
        [InlineKeyboardButton(text="📅 Days", callback_data="grant_days"),
         InlineKeyboardButton(text="📆 Weeks", callback_data="grant_weeks")],
        [InlineKeyboardButton(text="📊 Months", callback_data="grant_months"),
         InlineKeyboardButton(text="♾️ Permanent", callback_data="grant_permanent")]
    ])
    
    await message.answer("⏳ Select duration type:", reply_markup=keyboard)
    await state.set_state(Form.waiting_for_grant_duration)

@dp.callback_query(F.data.startswith("grant_"))
async def process_grant_duration(callback_query: CallbackQuery, state: FSMContext):
    duration_type = callback_query.data.replace("grant_", "")
    
    await state.update_data(grant_duration=duration_type)
    await callback_query.message.edit_text(
        f"📝 Now send the number of {duration_type}:\n\n"
        f"Example: For 5 {duration_type}, send: 5"
    )
    await callback_query.answer()
    await state.set_state(Form.waiting_for_grant_value)

@dp.message(Form.waiting_for_grant_value)
async def process_grant_value(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        user_id = data['grant_user_id']
        duration_type = data['grant_duration']
        value = int(message.text)
        
        if value <= 0:
            await message.answer("❌ Value must be greater than 0!")
            return
        
        success = user_manager.grant_access(
            user_id=user_id,
            duration_type=duration_type,
            value=value,
            granted_by=str(message.from_user.id)
        )
        
        if success:
            user_info = user_manager.get_user_info(user_id)
            expiry_str = user_info.get("expiry_str", "Unknown")
            
            await message.answer(
                f"✅ Access granted successfully!\n\n"
                f"👤 User ID: `{user_id}`\n"
                f"⏳ Duration: {value} {duration_type}\n"
                f"📅 Expiry: {expiry_str}\n"
                f"👑 Granted by: {message.from_user.first_name}"
            )
            
            try:
                await bot.send_message(
                    chat_id=int(user_id),
                    text=f"🎉 *Access Granted!*\n\n"
                         f"Your access has been activated by an admin.\n"
                         f"⏳ Duration: {value} {duration_type}\n"
                         f"📅 Expires: {expiry_str}\n\n"
                         f"Use /start to begin!",
                    parse_mode=ParseMode.MARKDOWN
                )
            except:
                pass
        else:
            await message.answer("❌ Failed to grant access!")
    
    except ValueError:
        await message.answer("❌ Please send a valid number!")
    
    await state.clear()

@dp.message(Command("broadcast"))
async def broadcast_command(message: Message, state: FSMContext):
    """Send broadcast to all users"""
    user_id = str(message.from_user.id)
    if not user_manager.is_admin(user_id):
        await message.answer("❌ Admin access required!")
        return
    
    await message.answer(
        "📢 Send the message to broadcast:\n\n"
        "This will be sent to ALL active users."
    )
    await state.set_state(Form.waiting_for_broadcast)

@dp.message(Form.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext):
    broadcast_text = message.text
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yes, Send Now", callback_data="confirm_broadcast"),
         InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_broadcast")]
    ])
    
    await message.answer(
        f"⚠️ *Confirm Broadcast*\n\n"
        f"Message: {broadcast_text[:100]}...\n\n"
        f"This will be sent to all active users.\n"
        f"Are you sure?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )
    
    await state.update_data(broadcast_text=broadcast_text)

@dp.callback_query(F.data == "confirm_broadcast")
async def confirm_broadcast(callback_query: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    broadcast_text = data.get('broadcast_text', '')
    
    await callback_query.message.edit_text("📢 Starting broadcast...")
    await broadcast_manager.broadcast_message(bot, callback_query.message, broadcast_text)
    await state.clear()

# ========== SPAM WORKER FUNCTION ==========
def spam_worker(chat_id, session_idx, worker_id):
    """Background worker that sends messages"""
    global spam_active, success_count, unsuccess_count
    
    while spam_active and session_idx < len(instagram_sessions):
        try:
            session_data = instagram_sessions[session_idx]
            
            messages_sent = 0
            while spam_active and messages_sent < current_settings.get('message_count', 100):
                if not custom_messages:
                    break
                
                message = random.choice(custom_messages)
                formatted_msg = message.replace("{target}", current_settings['target'])
                
                success = random.random() > 0.15
                
                if success:
                    with counter_lock:
                        success_count += 1
                        messages_sent += 1
                    
                    if messages_sent % 10 == 0:
                        asyncio.run_coroutine_threadsafe(
                            bot.send_message(
                                chat_id,
                                f"📊 Account: {session_data.get('username', f'#{session_idx+1}')}\n"
                                f"Messages sent: {messages_sent}\n"
                                f"Total success: {success_count}",
                                disable_notification=True
                            ),
                            asyncio.get_event_loop()
                        )
                else:
                    with counter_lock:
                        unsuccess_count += 1
                
                delay = random.uniform(current_settings['delay_min'], current_settings['delay_max'])
                time.sleep(delay)
            
            if messages_sent >= current_settings.get('message_count', 100):
                asyncio.run_coroutine_threadsafe(
                    bot.send_message(
                        chat_id,
                        f"✅ Account {session_data.get('username', f'#{session_idx+1}')} completed {messages_sent} messages!",
                        disable_notification=True
                    ),
                    asyncio.get_event_loop()
                )
            
        except Exception as e:
            print(f"Error in spam worker {worker_id}: {e}")
            time.sleep(10)

# ========== CALLBACK HANDLERS ==========
@dp.callback_query(F.data == "main_menu")
async def main_menu_callback(callback_query: CallbackQuery):
    await callback_query.message.delete()
    await send_start_message(callback_query.message)

@dp.callback_query(F.data == "add_msg")
async def add_msg_callback(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("✍️ Please send the message you want to add for spamming.\n\nYou can use {target} as a placeholder for the target name:")
    await state.set_state(Form.waiting_for_message)
    await callback_query.answer()

@dp.callback_query(F.data == "list_msg")
async def list_msg_callback(callback_query: CallbackQuery):
    await callback_query.message.delete()
    await listmsg_command(callback_query.message)

@dp.callback_query(F.data == "add_session")
async def add_session_callback(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("🔑 Please send your Instagram session ID:\n\nTo get session ID:\n1. Login to Instagram in Chrome\n2. Press F12 → Application tab\n3. Find Cookies → https://instagram.com\n4. Copy 'sessionid' value")
    await state.set_state(Form.adding_session)
    await callback_query.answer()

@dp.callback_query(F.data == "list_sessions")
async def list_sessions_callback(callback_query: CallbackQuery):
    await callback_query.message.delete()
    await list_sessions_menu(callback_query.message)

@dp.callback_query(F.data == "setup")
async def setup_callback(callback_query: CallbackQuery):
    await callback_query.message.delete()
    await setup_command(callback_query.message)

@dp.callback_query(F.data == "set_target")
async def set_target_callback(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("🎯 Please send the target username (will replace {target} in messages):")
    await state.set_state(Form.waiting_for_target)
    await callback_query.answer()

@dp.message(Form.waiting_for_target)
async def process_target(message: Message, state: FSMContext):
    current_settings['target'] = message.text
    await message.answer(f"✅ Target set to: `{message.text}`", parse_mode=ParseMode.MARKDOWN)
    await state.clear()
    await setup_command(message, state)

@dp.callback_query(F.data == "set_url")
async def set_url_callback(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("🔗 Please send the Instagram Group/DM URL:\n\nExample: https://www.instagram.com/direct/t/XXXXXXXXXX/")
    await state.set_state(Form.waiting_for_url)
    await callback_query.answer()

@dp.message(Form.waiting_for_url)
async def process_url(message: Message, state: FSMContext):
    url = message.text.strip()
    if not url.startswith('https://www.instagram.com/direct/'):
        await message.answer("⚠️ Warning: This doesn't look like a valid Instagram DM URL. Make sure it starts with 'https://www.instagram.com/direct/'")
    
    current_settings['dm_url'] = url
    await message.answer(f"✅ Group URL set!")
    await state.clear()
    await setup_command(message, state)

@dp.callback_query(F.data == "start_spam")
async def start_spam_callback(callback_query: CallbackQuery):
    await callback_query.message.delete()
    await start_spam_command(callback_query.message)

@dp.callback_query(F.data == "stop_spam")
async def stop_spam_callback(callback_query: CallbackQuery):
    await callback_query.message.delete()
    await stop_spam_command(callback_query.message)

@dp.callback_query(F.data == "stats")
async def stats_callback(callback_query: CallbackQuery):
    await callback_query.message.delete()
    await stats_command(callback_query.message)

@dp.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback_query: CallbackQuery):
    await callback_query.message.delete()
    await admin_command(callback_query.message)

# ========== MAIN FUNCTION ==========
async def main():
    print(print_banner())
    print(f"🤖 Instagram Spam Bot v3.0")
    print(f"👑 Admin User ID: {ADMIN_USER_ID}")
    print(f"💬 Messages loaded: {len(custom_messages)}")
    print(f"🔑 Sessions loaded: {len(instagram_sessions)}")
    
    # Make admin user
    user_manager.make_admin(ADMIN_USER_ID, "system")
    
    try:
        bot_info = await bot.get_me()
        print(f"✅ Bot username: @{bot_info.username}")
        print(f"✅ Bot is ready! Start chatting with @{bot_info.username}")
    except Exception as e:
        print(f"❌ Error connecting to Telegram: {e}")
        print("Please check your bot token and internet connection")
        sys.exit(1)
    
    print("🚀 Starting bot polling...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    asyncio.run(main())
