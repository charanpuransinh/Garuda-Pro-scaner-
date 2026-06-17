#!/bin/bash
# deploy.sh — Digital Ocean पर Garuda Power deploy करो
# Usage: bash scripts/deploy.sh

echo "🦅 GARUDA POWER — DEPLOY STARTING..."
echo "======================================"

# 1. System update
echo "📦 Step 1: System update..."
sudo apt update -y && sudo apt upgrade -y

# 2. Node.js install
echo "📦 Step 2: Node.js install..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# 3. Python install
echo "📦 Step 3: Python install..."
sudo apt install -y python3 python3-pip python3-venv

# 4. PM2 install (process manager)
echo "📦 Step 4: PM2 install..."
sudo npm install -g pm2

# 5. Nginx install
echo "📦 Step 5: Nginx install..."
sudo apt install -y nginx

# 6. Clone/Pull repo
echo "📦 Step 6: Code setup..."
if [ -d "/var/www/garuda-power" ]; then
  cd /var/www/garuda-power && git pull
else
  sudo git clone https://github.com/charanpuransinh/garuda-power /var/www/garuda-power
fi

cd /var/www/garuda-power

# 7. Python dependencies
echo "📦 Step 7: Python packages..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..

# 8. Node.js dependencies
echo "📦 Step 8: Node packages..."
cd backend && npm install && cd ..

# 9. Environment file
if [ ! -f "backend/.env" ]; then
  echo ""
  echo "⚠️  .env file नहीं है!"
  echo "     cp backend/.env.example backend/.env"
  echo "     nano backend/.env  (credentials fill करो)"
  echo ""
fi

# 10. Nginx config
echo "📦 Step 9: Nginx config..."
sudo tee /etc/nginx/sites-available/garuda-power << 'NGINX'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/garuda-power /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx

# 11. PM2 start
echo "📦 Step 10: Starting server..."
cd /var/www/garuda-power/backend
pm2 delete garuda-power 2>/dev/null || true
pm2 start server.js --name garuda-power
pm2 save
pm2 startup

echo ""
echo "======================================"
echo "✅ DEPLOY COMPLETE!"
echo ""
echo "🌐 Your server: http://YOUR_DROPLET_IP"
echo "📊 Master Panel: http://YOUR_DROPLET_IP/master-panel.html"
echo "📡 API Status: http://YOUR_DROPLET_IP/api/status"
echo ""
echo "📝 Next steps:"
echo "   1. nano /var/www/garuda-power/backend/.env"
echo "   2. Angel One credentials fill karo"
echo "   3. pm2 restart garuda-power"
echo "======================================"
