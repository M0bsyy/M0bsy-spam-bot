#!/data/data/com.termux/files/usr/bin/bash
# Create empty data files for the bot

echo "Creating empty data files..."

# Create directories
mkdir -p instagram_bot_data bot_logs

# Create empty messages file
cat > instagram_bot_data/messages.json << 'EOF'
[
  "Hello {target}, this is a test message!",
  "Welcome {target} to our spam bot!",
  "This is spam message for {target}"
]
EOF

# Create empty sessions file
cat > instagram_bot_data/sessions.json << 'EOF'
[]
EOF

# Create empty users file
cat > users_data.json << 'EOF'
{}
EOF

echo "✅ Empty data files created!"
echo "📁 instagram_bot_data/messages.json"
echo "📁 instagram_bot_data/sessions.json"
echo "📁 users_data.json"
