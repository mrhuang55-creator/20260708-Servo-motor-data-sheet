#!/bin/bash
# ================================================================================
# 三菱 MR-J5 伺服馬達 AI 智慧健康診斷系統 — Linux / GCP 一鍵部署腳本
# ================================================================================

set -e

echo "=== [1/6] 更新系統套件並安裝 Python3, venv, Nginx ==="
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv python3-full nginx curl psmisc

echo "=== [2/6] 建立部署目錄 /opt/phm_system ==="
TARGET_DIR="/opt/phm_system"
sudo mkdir -p $TARGET_DIR
sudo chown -R $USER:$USER $TARGET_DIR

echo "=== [3/6] 複製專案檔案 ==="
cp -r ./* $TARGET_DIR/
cd $TARGET_DIR

echo "=== [4/6] 建立 Python 虛擬環境與安裝依賴包 ==="
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== [5/6] 配置 Systemd 常駐服務 ==="
sudo cp phm-backend.service /etc/systemd/system/phm-backend.service
sudo cp phm-frontend.service /etc/systemd/system/phm-frontend.service

# 清理舊程序與 Port 8000 佔用
sudo fuser -k 8000/tcp || true
sudo pkill -f "python3 server.py" || true

sudo systemctl daemon-reload
sudo systemctl enable phm-backend phm-frontend
sudo systemctl restart phm-backend phm-frontend

echo "=== [6/6] 配置 Nginx 反向代理 ==="
sudo cp nginx_phm.conf /etc/nginx/sites-available/phm
sudo ln -sf /etc/nginx/sites-available/phm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo "================================================================================"
echo " SUCCESS: 部署完成！"
echo " 後端 FastAPI 服務 (Port 8000) 狀態: $(systemctl is-active phm-backend)"
echo " 前端 Flask 服務 (Port 5000) 狀態:   $(systemctl is-active phm-frontend)"
echo " Nginx 伺服器 (Port 80) 狀態:       $(systemctl is-active nginx)"
echo " 請訪問: http://<YOUR_SERVER_IP>/"
echo "================================================================================"
