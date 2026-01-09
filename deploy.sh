#!/data/data/com.termux/files/usr/bin/bash
# Instagram Bot Deployment Script for Termux

echo "╔══════════════════════════════════════════╗"
echo "║   INSTAGRAM BOT DEPLOYMENT              ║"
echo "║   Complete 24/7 System                  ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if running in Termux
if [ ! -d "/data/data/com.termux/files/usr" ]; then
    print_error "This script must be run in Termux!"
    exit 1
fi

print_status "Starting Instagram Bot Deployment..."

# Step 1: Update Termux packages
print_status "Step 1: Updating Termux packages..."
pkg update -y && pkg upgrade -y
pkg install -y python git wget curl termux-api termux-services

# Step 2: Install Python packages
print_status "Step 2: Installing Python packages..."
pip install --upgrade pip
pip install aiogram==3.7.0 beautifulsoup4 aiohttp requests python-dotenv colorama aiofiles

# Step 3: Create project directory
print_status "Step 3: Setting up project directory..."
if [ -d "instagram-bot" ]; then
    print_warning "instagram-bot directory already exists, updating..."
    cd instagram-bot
    git pull 2>/dev/null || echo "Not a git repository, continuing..."
else
    mkdir -p instagram-bot
    cd instagram-bot
fi

# Step 4: Create necessary directories
print_status "Step 4: Creating directories..."
mkdir -p instagram_bot_data bot_logs

# Step 5: Create configuration file if not exists
print_status "Step 5: Setting up configuration..."
if [ ! -f "config.py" ]; then
    cat > config.py << 'EOF'
# Instagram Bot Configuration
# Replace these values with your own

# Telegram Bot Token from @BotFather
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# Your Telegram User ID (get from @userinfobot)
ADMIN_ID = "YOUR_USER_ID_HERE"

# Auto-restart settings
AUTO_RESTART = True
RESTART_DELAY = 10  # seconds

# Logging settings
LOG_LEVEL = "INFO"
EOF
    print_warning "Please edit config.py with your BOT_TOKEN and ADMIN_ID"
fi

# Step 6: Make scripts executable
print_status "Step 6: Setting up scripts..."
chmod +x deploy.sh 2>/dev/null || true

# Step 7: Setup auto-start
print_status "Step 7: Setting up auto-start..."
python service_manager.py --setup 2>/dev/null || echo "Run this after creating service_manager.py"

# Step 8: Display instructions
echo ""
echo "╔══════════════════════════════════════════╗"
echo "║         DEPLOYMENT COMPLETE!            ║"
echo "╚══════════════════════════════════════════╝"
echo ""
print_success "✅ Instagram Bot has been deployed!"
echo ""
echo "📋 NEXT STEPS:"
echo "1. Edit config.py with your:"
echo "   - BOT_TOKEN (from @BotFather)"
echo "   - ADMIN_ID (from @userinfobot)"
echo ""
echo "2. Start the bot:"
echo "   cd instagram-bot"
echo "   python service_manager.py"
echo ""
echo "3. For 24/7 operation:"
echo "   - The bot will auto-restart if crashed"
echo "   - Setup auto-start with: python service_manager.py --setup"
echo ""
echo "📱 BOT COMMANDS:"
echo "   /start - Show all commands"
echo "   /addmsg - Add spam messages"
echo "   /addsession - Add Instagram accounts"
echo "   /start_spam - Start spamming"
echo "   /admin - Admin panel (admin only)"
echo ""
echo "🔧 ADMIN FEATURES:"
echo "   - Grant/revoke user access"
echo "   - Broadcast messages to all users"
echo "   - Manage user subscriptions"
echo ""
echo "📊 MONITORING:"
echo "   tail -f bot_logs/service.log"
echo ""
echo "🛑 TO STOP:"
echo "   Press Ctrl+C or: pkill -f service_manager.py"
echo ""
print_warning "⚠️ WARNING: Use responsibly and follow Instagram's Terms of Service!"
echo ""
