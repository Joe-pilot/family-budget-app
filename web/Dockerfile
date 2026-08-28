FROM nginxinc/nginx-unprivileged:1.31-alpine

USER root
RUN apk add --no-cache gettext \
    && apk upgrade --no-cache \
    && apk del curl \
    && rm -rf /var/cache/apk/*

COPY --chown=101:101 index.html style.css app.js config.template.js chart.umd.js /usr/share/nginx/html/
COPY --chown=101:101 nginx.conf /etc/nginx/conf.d/default.conf
COPY --chown=101:101 entrypoint.sh /entrypoint.sh
RUN chmod 0555 /entrypoint.sh

EXPOSE 8080
USER 101:101
ENTRYPOINT ["/entrypoint.sh"]
