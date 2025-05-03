#!/bin/bash

# Configuration
BACKUP_DIR="/backup"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
POSTGRES_CONTAINER="boturist_db_1"
MONGO_CONTAINER="boturist_mongodb_1"
RETENTION_DAYS=7

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
echo "Starting PostgreSQL backup..."
docker exec $POSTGRES_CONTAINER pg_dump -U boturist boturist | gzip > "$BACKUP_DIR/postgres_$TIMESTAMP.sql.gz"

# Backup MongoDB
echo "Starting MongoDB backup..."
docker exec $MONGO_CONTAINER mongodump --archive | gzip > "$BACKUP_DIR/mongodb_$TIMESTAMP.archive.gz"

# Backup Redis
echo "Starting Redis backup..."
docker exec boturist_redis_1 redis-cli SAVE
docker cp boturist_redis_1:/data/dump.rdb "$BACKUP_DIR/redis_$TIMESTAMP.rdb"

# Clean up old backups
find $BACKUP_DIR -name "postgres_*.sql.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "mongodb_*.archive.gz" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "redis_*.rdb" -mtime +$RETENTION_DAYS -delete

echo "Backup completed successfully!" 