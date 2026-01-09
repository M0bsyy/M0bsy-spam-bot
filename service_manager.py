#!/data/data/com.termux/files/usr/bin/python3
import os
import sys
import time
import subprocess
import signal

def run_bot_forever():
    """Run bot with auto-restart"""
    print("🤖 Instagram Bot 24/7 Service")
    print("="*50)
    
    restart_count = 0
    max_restarts = 100
    
    while restart_count < max_restarts:
        try:
            print(f"\n🚀 Starting bot (attempt {restart_count + 1})...")
            process = subprocess.Popen(
                [sys.executable, "instagram_bot.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            print(f"✅ Bot started with PID: {process.pid}")
            print("📁 Logs are being saved")
            
            # Wait for process to complete
            process.wait()
            
            # Check exit code
            if process.returncode == 0:
                print("Bot stopped normally")
                break
            else:
                stdout, stderr = process.communicate()
                if stderr:
                    print(f"❌ Bot error: {stderr[:200]}")
                
                restart_count += 1
                print(f"🔄 Restarting in 10 seconds... ({restart_count}/{max_restarts})")
                time.sleep(10)
                
        except KeyboardInterrupt:
            print("\n🛑 Service stopped by user")
            if process:
                process.terminate()
            break
        except Exception as e:
            print(f"❌ Service error: {e}")
            time.sleep(30)

if __name__ == "__main__":
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\n🛑 Received shutdown signal")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    run_bot_forever()
