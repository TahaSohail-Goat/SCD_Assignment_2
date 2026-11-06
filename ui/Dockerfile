FROM nginxinc/nginx-unprivileged:1.30.6-alpine3.24-slim
USER root
RUN apk upgrade --no-cache
COPY --chown=101:101 nginx.conf /etc/nginx/nginx.conf
COPY --chown=101:101 index.html /usr/share/nginx/html/index.html
USER 101:101
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
