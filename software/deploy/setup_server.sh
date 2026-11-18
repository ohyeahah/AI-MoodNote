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
need_user() { [ "$(id -u)" -ne 0 ] || { echo "root 가 아니라 일반 계정(ubuntu)으로 실행해 주세요."; exit 1; }; }
rand() { openssl rand -base64 36 | tr -d '/+=\n' | cut -c1-32; }

build_frontend() {
  say "화면 만들기 (npm)"
  cd "$FRONTEND"
  NODE_OPTIONS="--max-old-space-size=900" npm ci --no-audit --no-fund
  NODE_OPTIONS="--max-old-space-size=900" npm run build
}

update_code() {
  say "코드 가져오기"
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
  say "백엔드 패키지"
  "$BACKEND/.venv/bin/pip" install -q -r "$BACKEND/requirements.txt"
  build_frontend
  sudo systemctl restart moodnote
  echo "업데이트 끝. DB 구조가 바뀐 커밋이면 migrate_vX_Y.py 를 따로 실행해야 해요."
  exit 0
fi

read -rp "서비스 주소(도메인). 예) 13-125-1-1.sslip.io : " DOMAIN
[ -n "$DOMAIN" ] || { echo "주소가 필요해요."; exit 1; }

say "1/9 메모리 보조 공간(스왑 2GB)"
if ! swapon --show | grep -q .; then
  sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile >/dev/null && sudo swapon /swapfile
  grep -q '^/swapfile' /etc/fstab || echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
else echo "이미 있어요."; fi

say "2/9 패키지 설치"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y git curl ca-certificates gnupg openssl \
  mysql-server python3-venv python3-pip nodejs npm debian-keyring debian-archive-keyring apt-transport-https

say "3/9 Caddy(https 자동 적용) 설치"
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor --yes -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
  sudo apt-get update -y && sudo apt-get install -y caddy
fi

say "4/9 MySQL 설정 (작은 서버용으로 메모리 절약, 외부 접속 차단)"
sudo tee /etc/mysql/mysql.conf.d/zz-moodnote.cnf >/dev/null <<CNF
[mysqld]
bind-address = 127.0.0.1
performance_schema = OFF
innodb_buffer_pool_size = 128M
max_connections = 40
CNF
sudo systemctl enable --now mysql && sudo systemctl restart mysql

say "5/9 코드 받기"
update_code

say "6/9 백엔드 파이썬 환경"
cd "$BACKEND"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

say "7/9 DB 만들기"
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
  echo ".env 가 이미 있어서 DB 와 키는 그대로 둬요."
else
  APP_PW="$(rand)"
  DB_ADMIN_PASSWORD="$ADMIN_PW" DB_APP_PASSWORD="$APP_PW" \
    .venv/bin/python setup_db_mysql.py --user moodnote_admin --app-user moodnote_app
  read -rsp "OpenAI API 키 (없으면 그냥 Enter. 입력해도 화면에 안 보여요): " OPENAI; echo
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

say "8/9 화면 만들기 + 서버 등록"
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

say "9/9 매일 DB 백업 (최근 14개 보관)"
mkdir -p "$HOME/backups"
umask 077
printf '[client]\nuser=moodnote_admin\npassword=%s\n' "$ADMIN_PW" > "$HOME/.moodnote_backup.cnf"
CRON="0 19 * * * mysqldump --defaults-extra-file=$HOME/.moodnote_backup.cnf --single-transaction moodnote | gzip > $HOME/backups/moodnote_\$(date +\\%F).sql.gz && find $HOME/backups -name 'moodnote_*.sql.gz' -mtime +14 -delete"
( crontab -l 2>/dev/null | grep -v moodnote_backup.cnf; echo "$CRON" ) | crontab -

say "확인"
sleep 4
curl -s http://127.0.0.1:5001/api/health || true; echo
echo "서버 안: http://127.0.0.1:5001/api/health  / 밖: https://$DOMAIN/api/health"
echo
echo "★ 꼭 하세요: ENCRYPTION_KEY 를 비밀번호 관리자 등 서버 밖에 백업하세요. 잃으면 일기를 복구할 수 없어요."
echo "   (키 한 줄 보기: grep '^ENCRYPTION_KEY=' $BACKEND/.env  → 이 줄을 남에게 보내지 마세요)"
