# Multi-stage build for production-ready frontend
# Stage 1: Build
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package files
COPY package.json package-lock.json* ./

# Install dependencies
RUN npm install --legacy-peer-deps || npm install

# Copy source
COPY public ./public

# Build (if using React/Vue, would run build here)
RUN mkdir -p /app/dist && cp -r /app/public/* /app/dist/ 2>/dev/null || true


# Stage 2: Runtime - Use DEBIAN nginx (not Alpine) to avoid entrypoint script issues
FROM nginx:1.24

# Remove default nginx config
RUN rm -f /etc/nginx/conf.d/default.conf

# Create all required temp directories with proper permissions AS ROOT (before USER nginx)
RUN mkdir -p /tmp/nginx/{client_temp,proxy_temp,uwsgi_temp,scgi_temp} \
    && mkdir -p /var/cache/nginx \
    && mkdir -p /var/log/nginx \
    && chown -R nginx:nginx /tmp/nginx /var/cache/nginx /var/log/nginx \
    && chmod -R 755 /tmp/nginx /var/cache/nginx /var/log/nginx

# Copy custom nginx config (uses /tmp paths, no user directive)
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built static files from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html
COPY --from=builder /app/public /usr/share/nginx/html

# Ensure html directory permissions
RUN chown -R nginx:nginx /usr/share/nginx/html && chmod -R 755 /usr/share/nginx/html

# Switch to nginx user for security
USER nginx

EXPOSE 3000

# Start nginx directly
CMD ["nginx", "-g", "daemon off;"]
