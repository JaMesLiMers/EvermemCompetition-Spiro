#!/bin/bash
# EverMemOS Data Backup & Restore Script
# Usage:
#   ./scripts/backup_restore.sh backup    # Backup current data
#   ./scripts/backup_restore.sh restore   # Restore from backup

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${PROJECT_DIR}/backup"
MONGO_BACKUP="${BACKUP_DIR}/mongodb_dump"
DOCKER_COMPOSE="${PROJECT_DIR}/EverMemOS/docker-compose.yaml"
EVERMEMOS_DIR="${PROJECT_DIR}/EverMemOS"
EVERMEMOS_URL="${EVERMEMOS_BASE_URL:-http://localhost:1995}"

backup() {
    echo "==> Backing up EverMemOS data..."
    mkdir -p "${BACKUP_DIR}"

    # 1. Dump MongoDB (the single source of truth)
    echo "  [1/2] Dumping MongoDB..."
    rm -rf "${MONGO_BACKUP}"
    docker exec memsys-mongodb mongodump \
        --db memsys \
        --username admin \
        --password memsys123 \
        --authenticationDatabase admin \
        --out /tmp/mongodump \
        --quiet
    docker cp memsys-mongodb:/tmp/mongodump/memsys "${MONGO_BACKUP}"
    docker exec memsys-mongodb rm -rf /tmp/mongodump

    # 2. Record metadata
    echo "  [2/2] Recording metadata..."
    cat > "${BACKUP_DIR}/backup_meta.json" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "mongo_collections": $(docker exec memsys-mongodb mongosh --quiet --username admin --password memsys123 --authenticationDatabase admin --eval 'JSON.stringify(db.getSiblingDB("memsys").getCollectionNames())'),
    "notes": "Restore with: ./scripts/backup_restore.sh restore"
}
EOF

    echo ""
    echo "==> Backup complete!"
    echo "  Location: ${BACKUP_DIR}/"
    ls -lh "${MONGO_BACKUP}"/*.bson 2>/dev/null | awk '{printf "    %-40s %s\n", $NF, $5}'
    echo ""
}

restore() {
    echo "==> Restoring EverMemOS data from backup..."

    if [ ! -d "${MONGO_BACKUP}" ]; then
        echo "  ERROR: Backup not found at ${MONGO_BACKUP}"
        echo "  Run './scripts/backup_restore.sh backup' first"
        exit 1
    fi

    # 0. Make sure infrastructure is running
    echo "  [0/4] Checking infrastructure..."
    for port in 6379 27017 19200 19530; do
        if ! (echo > /dev/tcp/localhost/$port) 2>/dev/null; then
            echo "    Port $port not ready. Start infrastructure first: docker compose -f ${DOCKER_COMPOSE} up -d"
            exit 1
        fi
    done
    echo "    All infrastructure ports ready"

    # 1. Stop EverMemOS if running (to avoid conflicts)
    echo "  [1/4] Stopping EverMemOS service..."
    lsof -ti:1995 | xargs -r kill -9 2>/dev/null || true
    sleep 1

    # 2. Restore MongoDB
    echo "  [2/4] Restoring MongoDB..."
    docker cp "${MONGO_BACKUP}" memsys-mongodb:/tmp/mongorestore_data
    docker exec memsys-mongodb mongorestore \
        --db memsys \
        --username admin \
        --password memsys123 \
        --authenticationDatabase admin \
        --dir /tmp/mongorestore_data \
        --drop \
        --quiet
    docker exec memsys-mongodb rm -rf /tmp/mongorestore_data
    echo "    MongoDB restored"

    # 3. Start EverMemOS (needed for sync scripts)
    echo "  [3/4] Starting EverMemOS..."
    cd "${EVERMEMOS_DIR}" && nohup uv run python src/run.py > "${PROJECT_DIR}/logs/evermemos.log" 2>&1 &
    echo $! > "${PROJECT_DIR}/.evermemos.pid"

    # Wait for EverMemOS to be ready
    for i in $(seq 1 30); do
        if curl -sf "${EVERMEMOS_URL}/api/v1/memories/conversation-meta" > /dev/null 2>&1; then
            echo "    EverMemOS ready (PID: $(cat ${PROJECT_DIR}/.evermemos.pid))"
            break
        fi
        sleep 2
    done

    # 4. Rebuild ES and Milvus indexes from MongoDB
    echo "  [4/4] Rebuilding search indexes..."
    cd "${EVERMEMOS_DIR}"

    echo "    Syncing Elasticsearch (episodic_memory)..."
    uv run python src/bootstrap.py src/devops_scripts/data_fix/es_sync_docs.py \
        --index-name episodic-memory --batch-size 500 2>&1 | tail -3

    echo "    Syncing Milvus (episodic_memory)..."
    uv run python src/bootstrap.py src/devops_scripts/data_fix/milvus_sync_docs.py \
        --collection-name episodic_memory --batch-size 500 2>&1 | tail -3

    echo ""
    echo "==> Restore complete!"
    echo "  EverMemOS running at ${EVERMEMOS_URL}"
    echo "  PID: $(cat ${PROJECT_DIR}/.evermemos.pid)"
}

case "${1:-help}" in
    backup)
        backup
        ;;
    restore)
        restore
        ;;
    *)
        echo "Usage: $0 {backup|restore}"
        echo ""
        echo "  backup   - Dump MongoDB data to backup/"
        echo "  restore  - Restore MongoDB + rebuild ES/Milvus indexes"
        exit 1
        ;;
esac
