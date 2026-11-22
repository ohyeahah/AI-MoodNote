#!/usr/bin/env bash
# MoodNote 서버 설치 스크립트 (Ubuntu 24.04, Lightsail 서울 1GB 이상).
# 서버에 접속한 뒤 이 파일을 올려서 실행해요.
#   처음 설치:   bash setup_server.sh
#   코드 업데이트: bash setup_server.sh update
# 비밀번호와 키는 서버 안에서 만들어지거나 직접 입력해요. 이 스크립트에는 적혀 있지 않아요.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/ohyeahah/AI-MoodNote.git}"
BRANCH="${BRANCH:-frontend-social-login}"
APP_DIR="$HOME/MoodNote"
BACKEND="$APP_DIR/software/backend"
FRONTEND="$APP_DIR/software/frontend"
ADMIN_PW_FILE="$HOME/.moodnote_admin_pw"

say() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
need_user() { [ "$(id -u)" -ne 0 ] || { echo "Please run as a normal user (ubuntu), not root."; exit 1; }; }
rand() { openssl rand -base64 36 | tr -d '/+=\n' | cut -c1-32; }

build_frontend() {
  say "Building the frontend (npm)"
  cd "$FRONTEND"
  NODE_OPTIONS="--max-old-space-size=900" npm ci --no-audit --no-fund
  NODE_OPTIONS="--max-old-space-size=900" npm run build
}

update_code() {
  say "Fetching the code"
  if [ -d "$APP_DIR/.git" ]; then
    git -C "$APP_DIR" fetch origin "$BRANCH"
    git -C "$APP_DIR" checkout "$BRANCH"
    git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
  else
    git clone --branch "$BRANCH" "$REPO_URL" "$APP_DIR"
  fi
}

need_user

if [ "${1:-}" = "update" ]; then
  update_code
  say "Backend packages"
  "$BACKEND/.venv/bin/pip" install -q -r "$BACKEND/requirements.txt"
  build_frontend
  sudo systemctl restart moodnote
  echo "Update finished. If this commit changed the DB schema, run the matching migrate_vX_Y.py separately."
  exit 0
fi

read -rp "Service domain, e.g. 52-64-236-218.sslip.io : " DOMAIN
[ -n "$DOMAIN" ] || { echo "A domain is required."; exit 1; }

say "1/9 Swap space (2GB)"
if ! swapon --show | grep -q .; then
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile >/dev/null && sudo swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
else echo "Already exists."; fi

say "2/9 Installing packages"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git curl ca-certificates gnupg openssl \
  mysql-server python3-venv python3-pip nodejs npm debian-keyring debian-archive-keyring apt-transport-https

say "3/9 Installing Caddy (automatic HTTPS)"
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  sudo apt-get update -y && sudo apt-get install -y caddy
fi

say "4/9 Configuring MySQL (low memory, local access only)"
sudo tee /etc/mysql/mysql.conf.d/zz-moodnote.cnf >/dev/null <<CNF
[mysqld]
bind-address = 127.0.0.1
performance_schema = OFF
innodb_buffer_pool_size = 128M
max_connections = 40
CNF
sudo systemctl enable --now mysql && sudo systemctl restart mysql

say "5/9 Getting the code"
update_code

say "6/9 Backend Python environment"
cd "$BACKEND"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

say "7/9 Creating the database"
if [ ! -f "$ADMIN_PW_FILE" ]; then
  ADMIN_PW="$(rand)"
  sudo mysql <<SQL
CREATE USER IF NOT EXISTS 'moodnote_admin'@'localhost' IDENTIFIED BY '$ADMIN_PW';
ALTER USER 'moodnote_admin'@'localhost' IDENTIFIED BY '$ADMIN_PW';
GRANT ALL PRIVILEGES ON *.* TO 'moodnote_admin'@'localhost' WITH GRANT OPTION;
SQL
  umask 077; printf '%s' "$ADMIN_PW" > "$ADMIN_PW_FILE"
fi
ADMIN_PW="$(cat "$ADMIN_PW_FILE")"
if [ -f "$BACKEND/.env" ]; then
  echo ".env already exists, so the DB and keys are left unchanged."
else
  APP_PW="$(rand)"
  DB_ADMIN_PASSWORD="$ADMIN_PW" DB_APP_PASSWORD="$APP_PW" \
    .venv/bin/python setup_db_mysql.py --user moodnote_admin --app-user moodnote_app
  read -rsp "OpenAI API key (press Enter to skip; input is hidden): " OPENAI; echo
  JWT="$(.venv/bin/python -c 'import secrets;print(secrets.token_urlsafe(48))')"
  ENC="$(.venv/bin/python -c 'from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())')"
  umask 077
  cat > "$BACKEND/.env" <<ENV
JWT_SECRET_KEY=$JWT
ENCRYPTION_KEY=$ENC
DB_HOST=127.0.0.1
DB_USER=moodnote_app
DB_PASSWORD=$APP_PW
DB_NAME=moodnote
CORS_ORIGINS=https://$DOMAIN
OPENAI_API_KEY=$OPENAI
ENV
  unset OPENAI JWT ENC APP_PW
fi

say "8/9 Building the frontend + registering the service"
build_frontend
sudo tee /etc/systemd/system/moodnote.service >/dev/null <<UNIT
[Unit]
Description=MoodNote API
After=network.target mysql.service

[Service]
User=$USER
WorkingDirectory=$BACKEND
Environment=APP_ENV=production
ExecStart=$BACKEND/.venv/bin/gunicorn -w 2 -b 127.0.0.1:5001 --timeout 60 app:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT
sudo chmod 644 /etc/systemd/system/moodnote.service
sudo systemctl daemon-reload && sudo systemctl enable --now moodnote && sudo systemctl restart moodnote

sudo tee /etc/caddy/Caddyfile >/dev/null <<CADDY
$DOMAIN {
  encode gzip
  reverse_proxy 127.0.0.1:5001
}
CADDY
sudo chmod 644 /etc/caddy/Caddyfile
sudo systemctl reload caddy || sudo systemctl restart caddy

say "9/9 Daily DB backup (keeps the last 14)"
mkdir -p "$HOME/backups"
umask 077
printf '[client]\nuser=moodnote_admin\npassword=%s\n' "$ADMIN_PW" > "$HOME/.moodnote_backup.cnf"
CRON="0 19 * * * mysqldump --defaults-extra-file=$HOME/.moodnote_backup.cnf --single-transaction moodnote | gzip > $HOME/backups/moodnote_\$(date +\\%F).sql.gz && find $HOME/backups -name 'moodnote_*.sql.gz' -mtime +14 -delete"
( crontab -l 2>/dev/null | grep -v moodnote_backup.cnf; echo "$CRON" ) | crontab -

say "Health check"
sleep 4
curl -s http://127.0.0.1:5001/api/health || true; echo
echo "Inside the server: http://127.0.0.1:5001/api/health  /  Outside: https://$DOMAIN/api/health"
echo
echo "IMPORTANT: back up ENCRYPTION_KEY outside the server (e.g. in a password manager). If it is lost, diary entries cannot be recovered."
echo "   (To view the key line: grep '^ENCRYPTION_KEY=' $BACKEND/.env  -> never send this line to anyone)"
