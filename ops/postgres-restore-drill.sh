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
      log "KINUA restore drill: unsupported database URL scheme" >&2
      return 1
      ;;
  esac
}

if [ "${RESTORE_DRILL_CONFIRM:-}" != "KINUA_DISPOSABLE_ONLY" ]; then
  log "KINUA restore drill: refused; set RESTORE_DRILL_CONFIRM=KINUA_DISPOSABLE_ONLY" >&2
  exit 20
fi

: "${RESTORE_DATABASE_URL:?RESTORE_DATABASE_URL is required}"
: "${S3_ENDPOINT_URL:?S3_ENDPOINT_URL is required}"
: "${S3_BUCKET:?S3_BUCKET is required}"

export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-${S3_ACCESS_KEY_ID:-}}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-${S3_SECRET_ACCESS_KEY:-}}"
export AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-${S3_REGION:-auto}}"
: "${AWS_ACCESS_KEY_ID:?S3/AWS access key is required}"
: "${AWS_SECRET_ACCESS_KEY:?S3/AWS secret key is required}"

BACKUP_PREFIX="${BACKUP_PREFIX:-backups/postgres}"
TARGET_URL="$(normalize_database_url "$RESTORE_DATABASE_URL")"
SOURCE_URL=""
if [ -n "${DATABASE_URL:-}" ]; then
  SOURCE_URL="$(normalize_database_url "$DATABASE_URL")"
fi
if [ -n "$SOURCE_URL" ] && [ "$SOURCE_URL" = "$TARGET_URL" ]; then
  log "KINUA restore drill: target matches source database; refusing destructive restore" >&2
  exit 21
fi

KEY="${RESTORE_BACKUP_KEY:-}"
if [ -z "$KEY" ]; then
  KEY="$(aws --endpoint-url "$S3_ENDPOINT_URL" s3api list-objects-v2     --bucket "$S3_BUCKET"     --prefix "${BACKUP_PREFIX%/}/kinua-"     --query "reverse(sort_by(Contents[?ends_with(Key, '.custom')], &LastModified))[0].Key"     --output text)"
fi
if [ -z "$KEY" ] || [ "$KEY" = "None" ]; then
  log "KINUA restore drill: no backup found" >&2
  exit 22
fi

FILE="/tmp/kinua-restore.custom"
SHA_FILE="${FILE}.sha256"
cleanup() {
  rm -f "$FILE" "$SHA_FILE"
}
trap cleanup EXIT HUP INT TERM

log "KINUA restore drill: downloading key=$KEY"
aws --endpoint-url "$S3_ENDPOINT_URL" s3 cp "s3://$S3_BUCKET/$KEY" "$FILE" --no-progress >/dev/null
aws --endpoint-url "$S3_ENDPOINT_URL" s3 cp "s3://$S3_BUCKET/${KEY}.sha256" "$SHA_FILE" --no-progress >/dev/null

EXPECTED_SHA="$(awk '{print $1}' "$SHA_FILE")"
ACTUAL_SHA="$(sha256sum "$FILE" | awk '{print $1}')"
if [ -z "$EXPECTED_SHA" ] || [ "$EXPECTED_SHA" != "$ACTUAL_SHA" ]; then
  log "KINUA restore drill: checksum mismatch" >&2
  exit 23
fi

pg_restore --list "$FILE" >/dev/null
pg_restore   --clean   --if-exists   --no-owner   --no-privileges   --dbname="$TARGET_URL"   "$FILE"

TABLES="$(psql "$TARGET_URL" -Atc "select count(*) from information_schema.tables where table_schema='public';")"
ALEMBIC="$(psql "$TARGET_URL" -Atc "select version_num from alembic_version limit 1;" 2>/dev/null || true)"
ESSENTIAL="$(psql "$TARGET_URL" -Atc "select count(*) from information_schema.tables where table_schema='public' and table_name in ('clinics','users','patients','assessments');")"

if [ "$TABLES" -lt 4 ] || [ "$ESSENTIAL" -ne 4 ] || [ -z "$ALEMBIC" ]; then
  log "KINUA restore drill: validation FAILED tables=$TABLES essentials=$ESSENTIAL alembic=${ALEMBIC:-missing}" >&2
  exit 24
fi

log "KINUA_RESTORE_DRILL overall=PASS key=$KEY tables=$TABLES alembic=$ALEMBIC"
