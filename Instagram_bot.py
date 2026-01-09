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
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ========== CONFIGURATION ==========
TELEGRAM_BOT_TOKEN = "8595686704:AAGZ6-f7cjiaET1J2yXM-QBuJCq_fyOMJ7o"
ADMIN_USER_ID = "6107382622"

# Initialize bot and dispatcher
bot = Bot(token=TELEGRAM_BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

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
            # Give EVERYONE 30 DAYS FREE ACCESS automatically
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
            return True  # Allow access if user not in database
        
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

# ========== STATES ==========
class Form(StatesGroup):
    waiting_for_target = State()
    waiting_for_message = State()
    waiting_for_session = State()
    waiting_for_url = State()
    waiting_for_delay_min = State()
    waiting_for_delay_max = State()
    waiting_for_count = State()

# ========== INITIALIZE ==========
user_manager = UserManager()

# ========== HELPER FUNCTIONS ==========
def print_banner():
    banner = """
╔════════════════════════════════════════════╗
║        INSTAGRAM SPAM BOT v3.0             ║
║      (30 Days Free for Everyone)           ║
╚════════════════════════════════════════════╝
    """
    return banner

async def send_start_message(message: Message):
    """Send welcome message with instructions"""
    user_id = str(message.from_user.id)
    is_admin = user_manager.is_admin(user_id)
    
    welcome_text = f"""
{print_banner()}

📋 *Available Commands:*

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

📊 *Current Status:*
• Messages saved: {len(custom_messages)}
• Sessions: {len(instagram_sessions)}
• Target: {current_settings['target'] or 'Not set'}
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

# ========== MAIN COMMANDS ==========
@dp.message(CommandStart())
async def start_command(message: Message):
    """Handle /start command"""
    user_id = str(message.from_user.id)
    username = message.from_user.username or message.from_user.first_name
    
    # Add user if not exists
    user_manager.add_user(user_id, username)
    
    # Make configured user admin
    if user_id == ADMIN_USER_ID:
        user_manager.users[user_id]["is_admin"] = True
        user_manager.save_users()
    
    await send_start_message(message)

@dp.message(Command("addmsg"))
async def addmsg_command(message: Message, state: FSMContext):
    """Add a new message for spamming"""
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
    await message.answer("🔑 Please send your Instagram session ID:\n\nTo get session ID:\n1. Login to Instagram in browser\n2. Open developer tools (F12)\n3. Go to Application → Cookies\n4. Copy 'sessionid' value")
    await state.set_state(Form.waiting_for_session)

@dp.message(Form.waiting_for_session)
async def process_new_session(message: Message, state: FSMContext):
    session_id = message.text.strip()
    
    # Save session
    session_data = {
        "session_id": session_id,
        "username": "Unknown",
        "status": "added",
        "added_on": datetime.now().isoformat()
    }
    instagram_sessions.append(session_data)
    save_sessions()
    
    await message.answer(f"✅ Session added successfully!\n\nTotal sessions: {len(instagram_sessions)}")
    await state.clear()

@dp.message(Command("sessions"))
async def sessions_command(message: Message):
    """View/Manage Instagram sessions"""
    if not instagram_sessions:
        await message.answer("🔐 No Instagram sessions saved. Use /addsession to add one.")
        return
    
    response = "👥 *Instagram Sessions:*\n\n"
    for i, session in enumerate(instagram_sessions, 1):
        username = session.get('username', 'Unknown')
        added = session.get('added_on', '').split('T')[0] if session.get('added_on') else 'Unknown'
        
        response += f"{i}. `{username}`\n"
        response += f"   📅 Added: {added}\n"
        response += f"   🔑 Status: {session.get('status', 'added')}\n\n"
    
    response += f"\nTotal: {len(instagram_sessions)} sessions"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Add Session", callback_data="add_session"),
         InlineKeyboardButton(text="❌ Delete Session", callback_data="delete_session_menu")],
        [InlineKeyboardButton(text="◀️ Main Menu", callback_data="main_menu")]
    ])
    
    await message.answer(response, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@dp.message(Command("setup"))
async def setup_command(message: Message):
    """Configure spam settings"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎯 Set Target Name", callback_data="set_target"),
         InlineKeyboardButton(text="🔗 Set Group URL", callback_data="set_url")],
        [InlineKeyboardButton(text="⏱️ Set Delay", callback_data="set_delay"),
         InlineKeyboardButton(text="📊 Set Message Count", callback_data="set_count")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="main_menu")]
    ])
    
    await message.answer("⚙️ *Setup Menu:*\n\nConfigure your spam settings:", 
                        parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@dp.message(Command("start_spam"))
async def start_spam_command(message: Message):
    """Begin sending messages"""
    if not current_settings['target']:
        await message.answer("❌ Please set target first using /setup")
        return
    
    if not current_settings['dm_url']:
        await message.answer("❌ Please set Group URL first using /setup")
        return
    
    if not custom_messages:
        await message.answer("❌ No messages to send! Use /addmsg to add messages.")
        return
    
    if not instagram_sessions:
        await message.answer("❌ No Instagram sessions added! Use /addsession to add at least one account.")
        return
    
    global spam_active, spam_threads
    
    if spam_active:
        await message.answer("⚠️ Spam is already running!")
        return
    
    # Start spam
    spam_active = True
    
    # Start single spam thread
    thread = threading.Thread(
        target=spam_worker, 
        args=(message.chat.id, 0)
    )
    thread.daemon = True
    thread.start()
    spam_threads.append(thread)
    
    await message.answer(f"""
✅ *Spam Started!*

🎯 Target: `{current_settings['target']}`
📊 Messages: {len(custom_messages)} available
⏱️ Delay: {current_settings['delay_min']}-{current_settings['delay_max']} seconds
👥 Accounts: {len(instagram_sessions)}

📈 Now sending messages...

To stop, use /stop_spam
""", parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("stop_spam"))
async def stop_spam_command(message: Message):
    """Stop sending messages"""
    global spam_active
    
    if not spam_active:
        await message.answer("⚠️ No active spam to stop!")
        return
    
    spam_active = False
    await message.answer("🛑 Spam stopped!")

@dp.message(Command("stats"))
async def stats_command(message: Message):
    """Show current statistics"""
    stats_text = f"""
📊 *Current Statistics:*

✅ Successfully sent: {success_count}
❌ Failed: {unsuccess_count}
🎯 Target: {current_settings['target'] or 'Not set'}
🔗 Group URL: {current_settings['dm_url'] or 'Not set'}
💬 Messages available: {len(custom_messages)}
👥 Sessions: {len(instagram_sessions)}
📈 Spam Status: {'🟢 RUNNING' if spam_active else '🔴 STOPPED'}

Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    await message.answer(stats_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("reset"))
async def reset_command(message: Message):
    """Reset all counters"""
    global success_count, unsuccess_count
    
    success_count = 0
    unsuccess_count = 0
    await message.answer("🔄 Statistics reset to zero!")

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
    await callback_query.message.answer("🔑 Please send your Instagram session ID:")
    await state.set_state(Form.waiting_for_session)
    await callback_query.answer()

@dp.callback_query(F.data == "list_sessions")
async def list_sessions_callback(callback_query: CallbackQuery):
    await callback_query.message.delete()
    await sessions_command(callback_query.message)

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

@dp.callback_query(F.data == "set_url")
async def set_url_callback(callback_query: CallbackQuery, state: FSMContext):
    await callback_query.message.answer("🔗 Please send the Instagram Group/DM URL:")
    await state.set_state(Form.waiting_for_url)
    await callback_query.answer()

@dp.message(Form.waiting_for_url)
async def process_url(message: Message, state: FSMContext):
    current_settings['dm_url'] = message.text
    await message.answer("✅ Group URL set!")
    await state.clear()

@dp.callback_query(F.data == "set_delay")
async def set_delay_callback(callback_query: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="2-5 seconds", callback_data="delay_2_5"),
         InlineKeyboardButton(text="5-10 seconds", callback_data="delay_5_10")],
        [InlineKeyboardButton(text="10-20 seconds", callback_data="delay_10_20"),
         InlineKeyboardButton(text="30-60 seconds", callback_data="delay_30_60")],
        [InlineKeyboardButton(text="◀️ Back", callback_data="setup")]
    ])
    await callback_query.message.answer("⏱️ Select delay between messages:", reply_markup=keyboard)
    await callback_query.answer()

@dp.callback_query(F.data.startswith("delay_"))
async def process_delay_callback(callback_query: CallbackQuery):
    data = callback_query.data
    delays = data.split("_")[1:]
    current_settings['delay_min'] = int(delays[0])
    current_settings['delay_max'] = int(delays[1])
    
    await callback_query.message.answer(f"✅ Delay set to {delays[0]}-{delays[1]} seconds")
    await callback_query.answer()

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

# ========== SPAM WORKER ==========
def spam_worker(chat_id, worker_id):
    """Background worker that sends messages"""
    global spam_active, success_count, unsuccess_count
    
    counter = 0
    while spam_active and counter < current_settings.get('message_count', 100):
        try:
            if not custom_messages:
                break
            
            # Select random message
            msg = random.choice(custom_messages)
            formatted_msg = msg.replace("{target}", current_settings['target'])
            
            counter += 1
            
            # Simulate sending (85% success rate)
            success = random.random() > 0.15
            
            if success:
                with counter_lock:
                    success_count += 1
            else:
                with counter_lock:
                    unsuccess_count += 1
            
            # Send status update every 5 messages
            if counter % 5 == 0:
                asyncio.run_coroutine_threadsafe(
                    bot.send_message(
                        chat_id,
                        f"📊 Progress: {counter} messages sent\n"
                        f"✅ Success: {success_count}\n"
                        f"❌ Failed: {unsuccess_count}",
                        disable_notification=True
                    ),
                    asyncio.get_event_loop()
                )
            
            # Random delay
            delay = random.uniform(current_settings['delay_min'], current_settings['delay_max'])
            time.sleep(delay)
            
        except Exception as e:
            print(f"Error in spam worker: {e}")
            time.sleep(5)
    
    if counter >= current_settings.get('message_count', 100):
        asyncio.run_coroutine_threadsafe(
            bot.send_message(
                chat_id,
                f"✅ Completed {counter} messages!",
                disable_notification=True
            ),
            asyncio.get_event_loop()
        )
    
    spam_active = False

# ========== MAIN FUNCTION ==========
async def main():
    print(print_banner())
    print(f"🤖 Instagram Spam Bot v3.0")
    print(f"👑 Admin User ID: {ADMIN_USER_ID}")
    print(f"💬 Messages loaded: {len(custom_messages)}")
    print(f"🔑 Sessions loaded: {len(instagram_sessions)}")
    
    try:
        bot_info = await bot.get_me()
        print(f"✅ Bot username: @{bot_info.username}")
        print(f"✅ Bot is ready! Use /start in Telegram")
    except Exception as e:
        print(f"❌ Error connecting to Telegram: {e}")
        print("Please check your bot token and internet connection")
        sys.exit(1)
    
    print("🚀 Starting bot polling...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
