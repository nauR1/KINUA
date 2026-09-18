FROM postgres:17-alpine
RUN apk add --no-cache aws-cli ca-certificates
COPY ops/postgres-backup.sh /usr/local/bin/kinua-postgres-backup
COPY ops/postgres-restore-drill.sh /usr/local/bin/kinua-postgres-restore-drill
RUN chmod 0555 /usr/local/bin/kinua-postgres-backup /usr/local/bin/kinua-postgres-restore-drill
ENTRYPOINT ["/usr/local/bin/kinua-postgres-backup"]
