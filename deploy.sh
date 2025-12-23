#!/bin/bash

# Configuration
PI_USER="pong"
PI_IP="172.17.17.102"
REMOTE_DIR="~/BDS"

# 1. Check for tokens.json
if [ ! -f "tokens.json" ]; then
    echo "❌ tokens.json not found!"
    echo "PLEASE RUN: 'python3 server.py' on this computer first."
    echo "This will verify Twitch Authentication and generate the tokens file."
    exit 1
fi

echo "🚀 Deploying BDS to $PI_USER@$PI_IP..."

# 2. Create Directory
echo "📂 Creating directory $REMOTE_DIR on Pi..."
ssh "$PI_USER@$PI_IP" "mkdir -p $REMOTE_DIR"

# 3. Copy Files
echo "📦 Copying files..."
scp server.py .env tokens.json requirements.txt index.html "$PI_USER@$PI_IP:$REMOTE_DIR/"

# 4. Setup Remote Environment
echo "⚙️  Setting up environment on Pi (this might take a minute)..."
ssh "$PI_USER@$PI_IP" "bash -s" <<EOF
    cd $REMOTE_DIR
    # Create venv if it doesn't exist
    if [ ! -d "venv" ]; then
        echo "   Creating Python virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate and install
    echo "   Installing dependencies..."
    source venv/bin/activate
    pip install -r requirements.txt
    
    echo "✅ Setup complete!"
    echo "   Run 'source venv/bin/activate && python server.py' to start."
EOF

echo "🎉 Deployment Finished!"
