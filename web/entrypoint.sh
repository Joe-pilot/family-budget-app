#!/bin/sh
set -e
: "${API_BASE_URL:=http://localhost:8000}"
: "${DEFAULT_CURRENCY:=SAR}"
: "${API_KEY:=}"
export API_BASE_URL DEFAULT_CURRENCY API_KEY
envsubst '${API_BASE_URL} ${DEFAULT_CURRENCY} ${API_KEY}' \
  < /usr/share/nginx/html/config.template.js \
  > /tmp/config.js
exec nginx -g "daemon off;"
