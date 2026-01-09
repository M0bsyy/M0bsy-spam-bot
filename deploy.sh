#!/data/data/com.termux/files/usr/bin/bash
# Instagram Bot Deployment

echo "Installing Instagram Bot..."

# Update packages
pkg update -y && pkg upgrade -y
pkg install python git -y

# Install Python packages
pip install --upgrade pip
pip install aiogram beautifulsoup4 aiohttp requests

# Create directories
mkdir -p ~/instagram-bot
cd ~/instagram-bot

# Clone from your GitHub
echo "Downloading from GitHub..."
git clone https://github.com/M0bsyy/M0bsy-spam-bot.git . 2>/dev/null || echo "Already cloned"

# Create data directories
mkdir -p instagram_bot_data bot_logs

# Make scripts executable
chmod +x deploy.sh 2>/dev/null || true

echo "✅ Installation complete!"
echo ""
echo "📋 Next steps:"
echo "1. Make sure your bot token is correct in instagram_bot.py"
echo "2. Run: python instagram_bot.py"
echo "3. For 24/7: python service_manager.py"
echo ""
echo "🤖 Bot will start and users can use it immediately!"
