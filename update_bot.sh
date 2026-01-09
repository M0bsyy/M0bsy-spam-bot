#!/data/data/com.termux/files/usr/bin/bash
# Update Instagram Bot

echo "🔄 Updating Instagram Bot..."

cd ~/instagram-bot

# Stop existing bot
echo "Stopping current bot..."
pkill -f service_manager.py 2>/dev/null
pkill -f instagram_bot.py 2>/dev/null
sleep 2

# Update from GitHub
if [ -d ".git" ]; then
    echo "Pulling latest changes from GitHub..."
    git pull
else
    echo "Not a git repository, skipping update..."
fi

# Update dependencies
echo "Updating Python packages..."
pip install --upgrade -r requirements.txt

# Restart bot
echo "Restarting bot..."
python service_manager.py &

echo "✅ Update complete! Bot is now running with latest version."
