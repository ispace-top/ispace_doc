#!/usr/bin/env bash
# =============================================================================
# iSpaceDoc — Docker Hub 镜像部署脚本
# 镜像: wapedkj/ispace-doc
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.deploy.yml"
ENV_FILE="$SCRIPT_DIR/.env"
ENV_EXAMPLE="$SCRIPT_DIR/.env.example"
DOCKER_IMAGE="${DOCKER_IMAGE:-wapedkj/ispace-doc}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
PROJECT_NAME="${PROJECT_NAME:-ispacedoc}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*"; }

# -----------------------------------------------------------------------------
# 生成 .env 文件（首次部署时交互式创建）
# -----------------------------------------------------------------------------
gen_env() {
    if [ -f "$ENV_FILE" ]; then
        log ".env 文件已存在，跳过生成。"
        return
    fi

    echo ""
    echo "============================================"
    echo "  iSpaceDoc — 初次部署配置"
    echo "============================================"
    echo ""

    # 生成随机密钥
    local secret_key
    secret_key=$(LC_ALL=C tr -dc 'A-Za-z0-9!#$%&()*+,-./:;<=>?@[]^_`{|}~' < /dev/urandom | head -c 50 || true)

    read -r -p "数据库密码 [自动生成]: " DB_PASSWORD
    DB_PASSWORD="${DB_PASSWORD:-$(LC_ALL=C tr -dc 'A-Za-z0-9' < /dev/urandom | head -c 16)}"

    read -r -p "应用端口 [10086]: " APP_PORT
    APP_PORT="${APP_PORT:-10086}"

    read -r -p "API 端口 [8000]: " API_PORT
    API_PORT="${API_PORT:-8000}"

    read -r -p "调试模式 (true/false) [false]: " DEBUG
    DEBUG="${DEBUG:-false}"

    cat > "$ENV_FILE" <<EOF
# iSpaceDoc 部署环境变量 — 由 deploy.sh 自动生成
# 修改后执行 ./deploy.sh restart 生效

# 数据库
DB_NAME=ispace
DB_USER=ispace
DB_PASSWORD=${DB_PASSWORD}

# Django 密钥（请妥善保管）
SECRET_KEY=${secret_key}

# 镜像版本（latest / 具体版本号如 0.9.0）
IMAGE_TAG=${IMAGE_TAG}

# 端口映射
APP_PORT=${APP_PORT}
API_PORT=${API_PORT}

# 调试模式
DEBUG=${DEBUG}
EOF

    log ".env 文件已生成: $ENV_FILE"
    echo ""
    warn "请检查 .env 文件中的配置，确认无误后执行:"
    warn "  $0 start"
}

# -----------------------------------------------------------------------------
# 拉取最新镜像
# -----------------------------------------------------------------------------
pull() {
    log "拉取镜像: ${DOCKER_IMAGE}:${IMAGE_TAG} ..."
    docker pull "${DOCKER_IMAGE}:${IMAGE_TAG}"
    log "镜像拉取完成。"
}

# -----------------------------------------------------------------------------
# docker compose 封装
# -----------------------------------------------------------------------------
dc() {
    docker compose \
        -f "$COMPOSE_FILE" \
        --env-file "$ENV_FILE" \
        -p "$PROJECT_NAME" \
        "$@"
}

# -----------------------------------------------------------------------------
# 启动 / 更新 / 停止 / 重启 / 状态 / 日志
# -----------------------------------------------------------------------------
start() {
    if [ ! -f "$ENV_FILE" ]; then
        err "缺少 .env 文件，请先执行: $0 init"
        exit 1
    fi
    log "启动所有服务..."
    dc up -d --remove-orphans
    log "服务已启动。"
    echo ""
    status
}

update() {
    if [ ! -f "$ENV_FILE" ]; then
        err "缺少 .env 文件，请先执行: $0 init"
        exit 1
    fi
    IMAGE_TAG="$(grep -E '^IMAGE_TAG=' "$ENV_FILE" | cut -d= -f2 || echo "latest")"
    pull
    log "使用新镜像重新部署..."
    dc up -d --remove-orphans
    log "更新完成。"
    echo ""
    status
}

stop() {
    log "停止所有服务..."
    dc down --remove-orphans
    log "服务已停止。"
}

restart() {
    log "重启所有服务..."
    dc restart
    log "重启完成。"
}

status() {
    echo ""
    echo "==================== 服务状态 ===================="
    dc ps
    echo ""
    echo "访问地址:"
    echo "  主应用:  http://localhost:${APP_PORT:-10086}"
    echo "  API:     http://localhost:${API_PORT:-8000}"
    echo ""
}

logs() {
    local svc="${1:-}"
    if [ -n "$svc" ]; then
        dc logs -f --tail=100 "$svc"
    else
        dc logs -f --tail=50
    fi
}

down_clean() {
    warn "此操作将删除所有容器、卷和数据，不可恢复！"
    read -r -p "确认？输入 yes 继续: " confirm
    if [ "$confirm" != "yes" ]; then
        log "已取消。"
        exit 0
    fi
    log "删除所有容器和卷..."
    dc down -v --remove-orphans
    log "清理完成。"
}

usage() {
    echo "用法: $0 <command> [args]"
    echo ""
    echo "命令:"
    echo "  init        首次部署 — 生成 .env 配置文件"
    echo "  start       启动所有服务"
    echo "  update      拉取最新镜像并重新部署"
    echo "  stop        停止所有服务"
    echo "  restart     重启所有服务"
    echo "  status      查看服务状态"
    echo "  logs [svc]  查看日志（可选指定服务名）"
    echo "  down        停止并删除所有容器和卷（危险）"
    echo ""
    echo "环境变量:"
    echo "  IMAGE_TAG   指定镜像版本，默认 latest"
    echo ""
    echo "示例:"
    echo "  $0 init              # 首次部署"
    echo "  $0 start             # 启动服务"
    echo "  IMAGE_TAG=0.9.0 $0 update  # 更新到指定版本"
}

# -----------------------------------------------------------------------------
# 入口
# -----------------------------------------------------------------------------
if [ $# -eq 0 ]; then
    usage
    exit 0
fi

case "$1" in
    init)      gen_env ;;
    start)     start ;;
    update)    update ;;
    stop)      stop ;;
    restart)   restart ;;
    status)    status ;;
    logs)      logs "${2:-}" ;;
    down)      down_clean ;;
    -h|--help|help) usage ;;
    *)
        err "未知命令: $1"
        usage
        exit 1
        ;;
esac