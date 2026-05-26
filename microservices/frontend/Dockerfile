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
# For now, we serve the public folder as-is
RUN mkdir -p /app/dist && cp -r /app/public/* /app/dist/ 2>/dev/null || true


# Stage 2: Runtime with Nginx
FROM nginx:alpine

# Create temp directories for nginx
RUN mkdir -p /tmp/nginx/client_temp \
             /tmp/nginx/proxy_temp \
             /tmp/nginx/uwsgi_temp \
             /tmp/nginx/scgi_temp \
    && chown -R nginx:nginx /tmp/nginx \
    && chmod -R 755 /tmp/nginx

# Create cache directory
RUN mkdir -p /usr/share/nginx/cache \
    && chown -R nginx:nginx /usr/share/nginx/cache

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Copy built static files from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html
COPY --from=builder /app/public /usr/share/nginx/html

# Run as nginx user (101)
USER nginx

# Health check
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:3000/health || exit 1

EXPOSE 3000

# Expose port
EXPOSE 3000

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:3000/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
