#!/usr/bin/env bash
set -Eeuo pipefail
IFS=$'\n\t'

APP_NAME="sysconta"
APP_USER="${APP_USER:-sysconta}"
APP_GROUP="${APP_GROUP:-sysconta}"
APP_PORT="${APP_PORT:-8000}"
APP_HOST="${APP_HOST:-127.0.0.1}"
DOMAIN="${DOMAIN:-_}"
DEPLOY_ROOT="${DEPLOY_ROOT:-/opt/sysconta}"
DEFAULT_REPO_URL="https://github.com/xicocrm/SysContas.git"
DEFAULT_REPO_BRANCH="cursor/sistema-sysconta-completo-52c3"
REPO_URL="${SYSCONTA_REPO_URL:-${DEFAULT_REPO_URL}}"
REPO_BRANCH="${SYSCONTA_REPO_BRANCH:-${DEFAULT_REPO_BRANCH}}"
SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CURRENT_DIR="${DEPLOY_ROOT}/current"
VENV_DIR="${DEPLOY_ROOT}/venv"
LOG_DIR="/var/log/sysconta"
SOURCE_CACHE_DIR="${DEPLOY_ROOT}/source"
SERVICE_FILE="/etc/systemd/system/sysconta.service"
NGINX_SITE="/etc/nginx/sites-available/sysconta"
NGINX_LINK="/etc/nginx/sites-enabled/sysconta"
HEALTH_URL="http://127.0.0.1:${APP_PORT}/health"
MAX_RETRIES="${MAX_RETRIES:-8}"
SEED_ADMIN_NAME="${SEED_ADMIN_NAME:-Administrador}"
SEED_ADMIN_EMAIL="${SEED_ADMIN_EMAIL:-admin@sysconta.com}"
SEED_ADMIN_PASSWORD="${SEED_ADMIN_PASSWORD:-Admin@123456}"
SEED_COMPANY_NAME="${SEED_COMPANY_NAME:-Empresa Principal}"
SEED_COMPANY_CNPJ="${SEED_COMPANY_CNPJ:-00000000000191}"

log() {
  printf '[%s] %s\n' "$(date '+%F %T')" "$*"
}

retry() {
  local attempts="$1"
  local wait_seconds="$2"
  local description="$3"
  shift 3
  local n=1
  until "$@"; do
    if (( n >= attempts )); then
      log "ERRO: falha definitiva em: ${description}"
      return 1
    fi
    log "ALERTA: falha em '${description}' (tentativa ${n}/${attempts}). Corrigindo e tentando novamente..."
    sleep "$wait_seconds"
    n=$((n + 1))
    wait_seconds=$((wait_seconds * 2))
  done
  return 0
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Execute como root: sudo bash installers/vps/install_sysconta.sh"
    exit 1
  fi
}

repair_apt() {
  dpkg --configure -a || true
  apt-get install -f -y || true
  apt-get clean || true
}

install_base_packages() {
  retry "${MAX_RETRIES}" 2 "apt update" apt-get update -y
  retry "${MAX_RETRIES}" 2 "apt package repair" repair_apt
  retry "${MAX_RETRIES}" 2 "instalar pacotes base" \
    apt-get install -y python3 python3-venv python3-pip curl git nginx openssl ca-certificates rsync
}

ensure_user_and_dirs() {
  getent group "${APP_GROUP}" >/dev/null 2>&1 || groupadd --system "${APP_GROUP}"
  id -u "${APP_USER}" >/dev/null 2>&1 || useradd --system --gid "${APP_GROUP}" --home-dir "${DEPLOY_ROOT}" --shell /usr/sbin/nologin "${APP_USER}"
  mkdir -p "${DEPLOY_ROOT}" "${CURRENT_DIR}" "${LOG_DIR}"
}

prepare_source() {
  # Prioriza a pasta onde o script esta versionado.
  if [[ -d "${SOURCE_ROOT}/app" ]]; then
    log "Usando fonte local (script-dir) em ${SOURCE_ROOT}"
    return 0
  fi

  # Fallback: se o operador estiver no repositorio certo, usa a cwd.
  if [[ -d "${PWD}/app" ]]; then
    SOURCE_ROOT="${PWD}"
    log "Usando fonte local (cwd) em ${SOURCE_ROOT}"
    return 0
  fi

  if [[ -z "${REPO_URL}" ]]; then
    log "ERRO: codigo-fonte nao encontrado e SYSCONTA_REPO_URL nao informado."
    return 1
  fi

  log "Fonte local nao encontrada. Clonando automaticamente ${REPO_URL} (branch ${REPO_BRANCH})..."
  rm -rf "${SOURCE_CACHE_DIR}"
  retry "${MAX_RETRIES}" 2 "clone do repositorio" \
    git clone --depth 1 --branch "${REPO_BRANCH}" "${REPO_URL}" "${SOURCE_CACHE_DIR}"

  if [[ ! -d "${SOURCE_CACHE_DIR}/app" ]]; then
    log "Branch clonada sem pasta app. Tentando checkout/fetch automatico..."
    retry "${MAX_RETRIES}" 2 "fetch branch alvo" \
      git -C "${SOURCE_CACHE_DIR}" fetch origin "${REPO_BRANCH}"
    retry "${MAX_RETRIES}" 2 "checkout branch alvo" \
      git -C "${SOURCE_CACHE_DIR}" checkout "${REPO_BRANCH}"
  fi

  if [[ ! -d "${SOURCE_CACHE_DIR}/app" ]]; then
    log "ERRO: repositorio clonado, mas pasta app nao foi encontrada."
    return 1
  fi

  SOURCE_ROOT="${SOURCE_CACHE_DIR}"
  log "Fonte pronta em ${SOURCE_ROOT}"
}

sync_source() {
  retry "${MAX_RETRIES}" 2 "sincronizar código para deploy" \
    rsync -a --delete \
      --exclude ".git" \
      --exclude ".venv" \
      --exclude "__pycache__" \
      --exclude "*.pyc" \
      "${SOURCE_ROOT}/" "${CURRENT_DIR}/"
  chown -R "${APP_USER}:${APP_GROUP}" "${DEPLOY_ROOT}"
}

ensure_env_file() {
  local env_file="${CURRENT_DIR}/.env"
  if [[ ! -f "${env_file}" ]]; then
    local secret
    secret="$(openssl rand -hex 32 2>/dev/null || true)"
    if [[ -z "${secret}" ]]; then
      secret="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"
    fi
    cat >"${env_file}" <<EOF
APP_NAME=SysConta API
ENVIRONMENT=prod
SECRET_KEY=${secret}
TOKEN_EXPIRE_MINUTES=1440
DATABASE_URL=sqlite:///./sysconta.db
EOF
  fi

  grep -q '^AUTO_SEED_ADMIN=' "${env_file}" || echo "AUTO_SEED_ADMIN=true" >> "${env_file}"
  grep -q '^SEED_ADMIN_NAME=' "${env_file}" || echo "SEED_ADMIN_NAME=${SEED_ADMIN_NAME}" >> "${env_file}"
  grep -q '^SEED_ADMIN_EMAIL=' "${env_file}" || echo "SEED_ADMIN_EMAIL=${SEED_ADMIN_EMAIL}" >> "${env_file}"
  grep -q '^SEED_ADMIN_PASSWORD=' "${env_file}" || echo "SEED_ADMIN_PASSWORD=${SEED_ADMIN_PASSWORD}" >> "${env_file}"
  grep -q '^SEED_COMPANY_NAME=' "${env_file}" || echo "SEED_COMPANY_NAME=${SEED_COMPANY_NAME}" >> "${env_file}"
  grep -q '^SEED_COMPANY_CNPJ=' "${env_file}" || echo "SEED_COMPANY_CNPJ=${SEED_COMPANY_CNPJ}" >> "${env_file}"

  chown "${APP_USER}:${APP_GROUP}" "${env_file}"
}

setup_python_env() {
  if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    retry "${MAX_RETRIES}" 2 "criar venv" python3 -m venv "${VENV_DIR}"
  fi

  retry "${MAX_RETRIES}" 2 "upgrade pip/setuptools/wheel" \
    "${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel

  retry "${MAX_RETRIES}" 2 "instalar requirements" \
    "${VENV_DIR}/bin/python" -m pip install -r "${CURRENT_DIR}/requirements.txt"
}

seed_admin_user() {
  retry "${MAX_RETRIES}" 2 "criar/ajustar admin inicial" \
    bash -c "cd '${CURRENT_DIR}' && ${VENV_DIR}/bin/python -m app.scripts.ensure_admin"
}

write_systemd_service() {
  cat >"${SERVICE_FILE}" <<EOF
[Unit]
Description=SysConta API Service
After=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${CURRENT_DIR}
EnvironmentFile=${CURRENT_DIR}/.env
ExecStart=${VENV_DIR}/bin/python -m uvicorn app.main:app --host ${APP_HOST} --port ${APP_PORT}
Restart=always
RestartSec=5
StandardOutput=append:${LOG_DIR}/sysconta.out.log
StandardError=append:${LOG_DIR}/sysconta.err.log

[Install]
WantedBy=multi-user.target
EOF
  systemctl daemon-reload
  retry "${MAX_RETRIES}" 2 "habilitar serviço systemd" systemctl enable sysconta.service
  retry "${MAX_RETRIES}" 2 "iniciar serviço systemd" systemctl restart sysconta.service
}

configure_nginx() {
  cat >"${NGINX_SITE}" <<EOF
server {
    listen 80;
    server_name ${DOMAIN};

    location / {
        proxy_pass http://${APP_HOST}:${APP_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
  ln -sfn "${NGINX_SITE}" "${NGINX_LINK}"
  rm -f /etc/nginx/sites-enabled/default || true
  retry "${MAX_RETRIES}" 2 "validar nginx config" nginx -t
  retry "${MAX_RETRIES}" 2 "reiniciar nginx" systemctl restart nginx
}

healthcheck_with_self_heal() {
  local tries=1
  while (( tries <= 20 )); do
    if curl -fsS "${HEALTH_URL}" >/dev/null 2>&1; then
      log "Healthcheck da API ok."
      return 0
    fi
    log "Healthcheck falhou (tentativa ${tries}/20). Executando autocorrecoes..."
    systemctl restart sysconta.service || true
    sleep 3
    tries=$((tries + 1))
  done
  return 1
}

fallback_docker_deploy() {
  log "Ativando fallback automatico via Docker..."
  retry "${MAX_RETRIES}" 2 "instalar docker.io" apt-get install -y docker.io
  retry "${MAX_RETRIES}" 2 "instalar docker compose plugin" \
    bash -c "apt-get install -y docker-compose-plugin || apt-get install -y docker-compose"
  systemctl enable docker || true
  systemctl restart docker || true
  systemctl stop sysconta.service || true

  if command -v docker >/dev/null 2>&1; then
    retry "${MAX_RETRIES}" 2 "docker compose build/up" \
      bash -c "cd '${CURRENT_DIR}' && (docker compose up -d --build || docker-compose up -d --build)"
  else
    log "ERRO: docker nao disponivel apos instalacao."
    return 1
  fi

  local attempts=1
  while (( attempts <= 20 )); do
    if curl -fsS "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
      log "Fallback Docker concluido com sucesso."
      return 0
    fi
    log "Aguardando API no Docker (tentativa ${attempts}/20)..."
    sleep 4
    attempts=$((attempts + 1))
  done
  return 1
}

main() {
  require_root
  log "Iniciando instalacao automatica do SysConta..."

  install_base_packages
  ensure_user_and_dirs
  prepare_source
  sync_source
  ensure_env_file
  setup_python_env
  seed_admin_user
  write_systemd_service
  configure_nginx

  if ! healthcheck_with_self_heal; then
    log "Falha na instalacao nativa. Iniciando correcao automatica com fallback..."
    fallback_docker_deploy
  fi

  log "INSTALACAO CONCLUIDA COM SUCESSO."
  log "Servico: $(systemctl is-active sysconta.service 2>/dev/null || echo 'docker-fallback')"
  log "Login inicial: ${SEED_ADMIN_EMAIL} / ${SEED_ADMIN_PASSWORD}"
  log "Acesse: http://$(hostname -I | awk '{print $1}')/docs"
}

main "$@"
