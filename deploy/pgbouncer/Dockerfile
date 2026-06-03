FROM alpine:3.20

RUN apk add --no-cache gettext pgbouncer postgresql-client \
    && (addgroup -S pgbouncer || true) \
    && (adduser -S -G pgbouncer pgbouncer || true) \
    && mkdir -p /run/pgbouncer \
    && chown -R pgbouncer:pgbouncer /run/pgbouncer

COPY pgbouncer.ini /etc/pgbouncer/pgbouncer.ini.template
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh

RUN chmod +x /usr/local/bin/docker-entrypoint.sh

USER pgbouncer

EXPOSE 6432

ENTRYPOINT ["docker-entrypoint.sh"]
