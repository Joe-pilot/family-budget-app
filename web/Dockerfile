FROM nginx:1.27-alpine

RUN apk add --no-cache gettext

COPY index.html style.css app.js config.template.js chart.umd.js /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["/entrypoint.sh"]
