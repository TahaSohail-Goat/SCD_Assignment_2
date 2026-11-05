FROM nginxinc/nginx-unprivileged:1.27.4-alpine
COPY --chown=101:101 nginx.conf /etc/nginx/nginx.conf
COPY --chown=101:101 index.html /usr/share/nginx/html/index.html
USER 101:101
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
