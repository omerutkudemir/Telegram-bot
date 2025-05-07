#!/bin/bash
set -e  # Hata olursa dur
# Sistem güncellemeleri ve bağımlılıklar
apt-get update
apt-get install -y wget unzip libglib2.0-0 libnss3 libgconf-2-4 libfontconfig1
# Chrome'u yükle
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
apt-get install -y ./google-chrome-stable_current_amd64.deb
rm google-chrome-stable_current_amd64.deb
# Chrome yolunu doğrula
if [ -f "/usr/bin/google-chrome" ]; then
    echo "Chrome başarıyla yüklendi"
else
    echo "HATA: Chrome yüklenemedi"
    exit 1
fi
# Python bağımlılıklarını yükle
pip install -r requirements.txt
