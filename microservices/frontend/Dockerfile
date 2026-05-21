FROM node:18-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --only=prod || true
COPY public ./public
EXPOSE 3000
CMD ["npx","http-server","public","-p","3000","-a","0.0.0.0"]
