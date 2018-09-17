#!/usr/bin/env bash
set -euov pipefail
# IFS=$'\n\t'

PROJECT_DIR="$(dirname "$(readlink -f "$0")")"

# проверим что не рут
if [ "$EUID" -eq 0 ]; then
    echo "Place project somewhere inside home."
    echo "And then run as normal user."
    exit 1
fi

# Проверим что зависимости установлены в системе
declare -a dependencies=('docker' 'python3.6' 'npm' 'node' 'gcc' 'sudo')
for dep in "${dependencies[@]}"; do
    if ! command -v "$dep" >/dev/null; then
        echo "$dep - not found! Install it."
        exit 2
    fi
done

# Скачиваем зависимости
npm --prefix "${PROJECT_DIR}/frontend" install

# Компилируем parcel'ем исходники страничек
npm --prefix "${PROJECT_DIR}/frontend" run build

# Создадим systemd unit
echo "
[Unit]
Description=Gunicorn instance to serve registration
After=network.target

[Service]
User=${USER}
Group=${USER}
WorkingDirectory=${PROJECT_DIR}/backend
Environment='PATH=${PROJECT_DIR}/backend/venv/bin'
ExecStart=${PROJECT_DIR}/backend/venv/bin/gunicorn --workers 3 --bind 0.0.0.0:5000 main:app

[Install]
WantedBy=multi-user.target
" | sudo tee /etc/systemd/system/registration.service >/dev/null

# Включаем регистрацию
sudo systemctl daemon-reload
sudo systemctl start registration
sudo systemctl enable registration
