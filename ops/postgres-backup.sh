#!/bin/sh
set -eu

log() {
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

normalize_database_url() {
  case "$1" in
    postgresql+psycopg://*)
      printf 'postgresql://%s' "${1#postgresql+psycopg://}"
      ;;
    postgresql://*|postgres://*)
      printf '%s' "$1"
      ;;
    *)
      log "KINUA backup: unsupported DATABASE_URL scheme" >&2
      return 1
      ;;
  esac
}

BACKUP_DATABASE_URL="${BACKUP_DATABASE_URL:-${DATABASE_URL:-}}"
: "${BACKUP_DATABASE_URL:?BACKUP_DATABASE_URL or DATABASE_URL is required}"
: "${S3_ENDPOINT_URL:?S3_ENDPOINT_URL is required}"
: "${S3_BUCKET:?S3_BUCKET is required}"

export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${S3_ACCESS_KEY_ID:-}}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-${S3_SECRET_ACCESS_KEY:-}}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-${S3_REGION:-auto}}"
: "${AWS_ACCESS_KEY_ID:?S3/AWS access key is required}"
: "${AWS_SECRET_ACCESS_KEY:?S3/AWS secret key is required}"

BACKUP_PREFIX="${BACKUP_PREFIX:-backups/postgres}"
BACKUP_KEEP_COUNT="${BACKUP_KEEP_COUNT:-30}"
BACKUP_PRUNE_ENABLED="${BACKUP_PRUNE_ENABLED:-false}"

case "$BACKUP_KEEP_COUNT" in
  ''|*[!0-9]*)
    log "KINUA backup: BACKUP_KEEP_COUNT must be an integer" >&2
    exit 2
    ;;
esac
if [ "$BACKUP_KEEP_COUNT" -lt 1 ]; then
  log "KINUA backup: BACKUP_KEEP_COUNT must be >= 1" >&2
  exit 2
fi

DB_URL="$(normalize_database_url "$BACKUP_DATABASE_URL")"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="/tmp/kinua-${TS}.custom"
SHA_FILE="${FILE}.sha256"
MANIFEST_FILE="${FILE}.manifest.json"
KEY="${BACKUP_PREFIX%/}/kinua-${TS}.custom"
SHA_KEY="${KEY}.sha256"
MANIFEST_KEY="${KEY}.manifest.json"

cleanup() {
  rm -f "$FILE" "$SHA_FILE" "$MANIFEST_FILE"
}
trap cleanup EXIT HUP INT TERM

log "KINUA backup: dump starting"
pg_dump "$DB_URL"   --format=custom   --no-owner   --no-privileges   --file="$FILE"

test -s "$FILE"
pg_restore --list "$FILE" >/dev/null

SIZE="$(wc -c < "$FILE" | tr -d ' ')"
SHA="$(sha256sum "$FILE" | awk '{print $1}')"
TABLES="$(psql "$DB_URL" -Atc "select count(*) from information_schema.tables where table_schema='public';")"
ALEMBIC="$(psql "$DB_URL" -Atc "select version_num from alembic_version limit 1;" 2>/dev/null || true)"

if [ -z "$ALEMBIC" ]; then
  log "KINUA backup: alembic_version unavailable; refusing to publish dump" >&2
  exit 3
fi

printf '%s  %s\n' "$SHA" "$(basename "$FILE")" > "$SHA_FILE"
cat > "$MANIFEST_FILE" <<EOF
{"created_at":"$(date -u +%Y-%m-%dT%H:%M:%SZ)","key":"$KEY","sha256":"$SHA","bytes":$SIZE,"public_tables":$TABLES,"alembic":"$ALEMBIC","format":"pg_dump_custom"}
EOF

aws --endpoint-url "$S3_ENDPOINT_URL" s3 cp "$FILE" "s3://$S3_BUCKET/$KEY" --no-progress >/dev/null
aws --endpoint-url "$S3_ENDPOINT_URL" s3 cp "$SHA_FILE" "s3://$S3_BUCKET/$SHA_KEY" --no-progress >/dev/null
aws --endpoint-url "$S3_ENDPOINT_URL" s3 cp "$MANIFEST_FILE" "s3://$S3_BUCKET/$MANIFEST_KEY" --no-progress >/dev/null

REMOTE_SIZE="$(aws --endpoint-url "$S3_ENDPOINT_URL" s3api head-object   --bucket "$S3_BUCKET"   --key "$KEY"   --query ContentLength   --output text)"
if [ "$REMOTE_SIZE" != "$SIZE" ]; then
  log "KINUA backup: remote size mismatch local=$SIZE remote=$REMOTE_SIZE" >&2
  exit 4
fi

log "KINUA backup: PASS key=$KEY bytes=$SIZE tables=$TABLES alembic=$ALEMBIC"

if [ "$BACKUP_PRUNE_ENABLED" = "true" ]; then
  OBJECTS="$(aws --endpoint-url "$S3_ENDPOINT_URL" s3api list-objects-v2     --bucket "$S3_BUCKET"     --prefix "${BACKUP_PREFIX%/}/kinua-"     --query "reverse(sort_by(Contents[?ends_with(Key, '.custom')], &LastModified))[].Key"     --output text)"
  INDEX=0
  for OLD_KEY in $OBJECTS; do
    INDEX=$((INDEX + 1))
    if [ "$INDEX" -le "$BACKUP_KEEP_COUNT" ]; then
      continue
    fi
    aws --endpoint-url "$S3_ENDPOINT_URL" s3 rm "s3://$S3_BUCKET/$OLD_KEY" >/dev/null
    aws --endpoint-url "$S3_ENDPOINT_URL" s3 rm "s3://$S3_BUCKET/${OLD_KEY}.sha256" >/dev/null || true
    aws --endpoint-url "$S3_ENDPOINT_URL" s3 rm "s3://$S3_BUCKET/${OLD_KEY}.manifest.json" >/dev/null || true
    log "KINUA backup: pruned key=$OLD_KEY"
  done
else
  log "KINUA backup: pruning disabled; no historical backup was deleted"
fi
