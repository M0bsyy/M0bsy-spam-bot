#!/data/data/com.termux/files/usr/bin/python3
import os
import sys
import time
import subprocess
import logging
import signal
from pathlib import Path

# Setup logging
LOG_DIR = Path("bot_logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'service.log'),
        logging.StreamHandler()
    ]
)

class BotService:
    def __init__(self):
        self.process = None
        self.bot_script = "instagram_bot.py"
        self.running = True
        
    def start_bot(self):
        """Start the bot process"""
        try:
            logging.info("🚀 Starting Instagram Bot...")
            self.process = subprocess.Popen(
                [sys.executable, self.bot_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            logging.info(f"✅ Bot started with PID: {self.process.pid}")
            return True
        except Exception as e:
            logging.error(f"❌ Failed to start bot: {e}")
            return False
    
    def monitor(self):
        """Monitor and restart bot if it crashes"""
        restart_count = 0
        max_restarts = 100
        
        while self.running and restart_count < max_restarts:
            if not self.process or self.process.poll() is not None:
                logging.warning(f"⚠️ Bot stopped. Restarting... (Attempt #{restart_count + 1})")
                
                # Read error output if any
                if self.process:
                    stdout, stderr = self.process.communicate()
                    if stderr:
                        logging.error(f"Bot error: {stderr}")
                
                # Restart the bot
                if self.start_bot():
                    restart_count += 1
                else:
                    logging.error("Failed to restart bot, waiting 30 seconds...")
                    time.sleep(30)
            
            # Check every 10 seconds
            time.sleep(10)
    
    def stop(self):
        """Stop the bot service"""
        self.running = False
        if self.process:
            logging.info("🛑 Stopping bot process...")
            self.process.terminate()
            try:
                self.process.wait(timeout=30)
                logging.info("✅ Bot stopped successfully")
            except subprocess.TimeoutExpired:
                self.process.kill()
                logging.warning("⚠️ Force killed bot process")

def setup_termux_boot():
    """Setup Termux boot service for auto-start"""
    boot_dir = Path.home() / ".termux/boot"
    boot_dir.mkdir(parents=True, exist_ok=True)
    
    boot_script = boot_dir / "start_instagram_bot"
    boot_script.write_text("""#!/data/data/com.termux/files/usr/bin/bash
# Instagram Bot Auto-Start on Termux Boot
echo "$(date): Starting Instagram Bot..." >> ~/instagram-bot/bot_logs/boot.log
cd ~/instagram-bot
python service_manager.py >> ~/instagram-bot/bot_logs/service.log 2>&1 &
""")
    
    boot_script.chmod(0o755)
    logging.info("✅ Boot script created at ~/.termux/boot/start_instagram_bot")
    print("✓ Auto-start configured! Bot will start automatically when Termux launches.")

def main():
    """Main service manager"""
    print("="*50)
    print("🤖 INSTAGRAM BOT 24/7 SERVICE MANAGER")
    print("="*50)
    
    # Handle command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--setup":
            setup_termux_boot()
            return
        elif sys.argv[1] == "--help":
            print("Usage:")
            print("  python service_manager.py          # Start service")
            print("  python service_manager.py --setup  # Setup auto-start")
            print("  python service_manager.py --help   # Show this help")
            return
    
    # Handle signals
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        service.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("Starting 24/7 service...")
    print("The bot will auto-restart if it crashes")
    print("Press Ctrl+C to stop the service")
    print("="*50)
    
    # Start the service
    service = BotService()
    
    if service.start_bot():
        print(f"✅ Bot started successfully!")
        print(f"📁 Logs: bot_logs/service.log")
        print(f"🔄 Auto-restart: Enabled")
        print("="*50)
        service.monitor()
    else:
        print("❌ Failed to start bot service")
        sys.exit(1)

if __name__ == "__main__":
    main()
