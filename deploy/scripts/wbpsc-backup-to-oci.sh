#!/usr/bin/env bash
# Create one database dump and one upload archive, then copy them to a private OCI bucket.
set -Eeuo pipefail
umask 077

: "${DB_NAME:?DB_NAME is required}"
: "${DB_USER:?DB_USER is required}"
: "${DB_PASSWORD:?DB_PASSWORD is required}"
: "${DB_HOST:?DB_HOST is required}"
: "${DB_PORT:?DB_PORT is required}"
: "${OCI_BUCKET_NAME:?OCI_BUCKET_NAME is required}"
: "${OCI_REGION:?OCI_REGION is required}"

backup_directory="$(mktemp -d /var/tmp/wbpsc-backup.XXXXXX)"
backup_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
database_backup="${backup_directory}/${DB_NAME}-${backup_stamp}.dump"
media_backup="${backup_directory}/media-${backup_stamp}.tar.gz"
media_directory="/srv/wbpsc-platform/shared/media"

cleanup() {
    rm -rf -- "$backup_directory"
}
trap cleanup EXIT

if [[ ! -d "$media_directory" ]]; then
    echo "Expected media directory is missing: ${media_directory}" >&2
    exit 1
fi

# pg_dump uses the service's protected DB_PASSWORD environment value; it is not put in argv.
PGPASSWORD="$DB_PASSWORD" pg_dump \
    --format=custom \
    --host="$DB_HOST" \
    --port="$DB_PORT" \
    --username="$DB_USER" \
    --no-password \
    --file="$database_backup" \
    "$DB_NAME"

tar --create --gzip --file="$media_backup" --directory=/srv/wbpsc-platform/shared media

oci os object put \
    --auth instance_principal \
    --region "$OCI_REGION" \
    --bucket-name "$OCI_BUCKET_NAME" \
    --name "postgres/${DB_NAME}-${backup_stamp}.dump" \
    --file "$database_backup" \
    --no-overwrite

oci os object put \
    --auth instance_principal \
    --region "$OCI_REGION" \
    --bucket-name "$OCI_BUCKET_NAME" \
    --name "media/media-${backup_stamp}.tar.gz" \
    --file "$media_backup" \
    --no-overwrite

echo "Uploaded database and media backups for ${backup_stamp}."
