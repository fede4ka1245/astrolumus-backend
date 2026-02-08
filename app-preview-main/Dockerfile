FROM node:18-alpine

RUN npm install pm2 -g

# Install chromium with retry logic to handle transient network errors
ENV CHROME_BIN=/usr/bin/chromium-browser

RUN echo @edge https://dl-cdn.alpinelinux.org/alpine/edge/community >> /etc/apk/repositories && \
    echo @edge https://dl-cdn.alpinelinux.org/alpine/edge/main >> /etc/apk/repositories && \
    for i in 1 2 3 4 5; do \
      apk add --no-cache \
        chromium@edge \
        nss@edge \
      && break || echo "Retry $i/5..." && sleep 10; \
    done

# Bundle APP files
COPY . /app/
WORKDIR /app/

ENV NPM_CONFIG_LOGLEVEL=warn

# Backend API Configuration (passed from docker-compose)
ARG BACKEND_URL
ARG BACKEND_API_TOKEN
ENV BACKEND_URL=$BACKEND_URL
ENV BACKEND_API_TOKEN=$BACKEND_API_TOKEN

RUN printenv > /app/.env

RUN npm install --production
RUN npx prisma generate
RUN /app/node_modules/next/dist/bin/next build
