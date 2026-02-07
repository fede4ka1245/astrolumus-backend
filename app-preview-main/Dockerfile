#FROM keymetrics/pm2:latest-alpine thos have the old version of pm2 with error
FROM node:14-alpine

RUN npm install pm2 -g

# Bundle APP files
COPY . /app/

#RUN apk update && apk del libressl-dev \
#  && apk add openssl-dev \
#  && apk del openssl-dev \
#  && apk add libressl-dev --allow-untrusted --repository="http://dl-cdn.alpinelinux.org/alpine/edge/community"
#RUN apk add --allow-untrusted --no-cache nodejs-current --repository="http://dl-cdn.alpinelinux.org/alpine/edge/community"

ENV NODE_PACKAGE_URL  https://unofficial-builds.nodejs.org/download/release/v18.16.0/node-v18.16.0-linux-x64-musl.tar.gz

RUN apk add libstdc++
WORKDIR /opt
RUN wget $NODE_PACKAGE_URL
RUN mkdir -p /opt/nodejs
RUN tar -zxvf *.tar.gz --directory /opt/nodejs --strip-components=1
RUN rm *.tar.gz
RUN ln -sf /opt/nodejs/bin/node /usr/local/bin/node
RUN ln -sf /opt/nodejs/bin/npm /usr/local/bin/npm

# Install app dependencies
WORKDIR /app/
ENV NPM_CONFIG_LOGLEVEL warn
ENV CHROME_BIN=/usr/bin/chromium-browser

# Backend API Configuration (passed from docker-compose)
ARG BACKEND_URL
ARG BACKEND_API_TOKEN
ENV BACKEND_URL=$BACKEND_URL
ENV BACKEND_API_TOKEN=$BACKEND_API_TOKEN
RUN echo @edge http://nl.alpinelinux.org/alpine/edge/community >> /etc/apk/repositories && \
    echo @edge http://nl.alpinelinux.org/alpine/edge/main >> /etc/apk/repositories && \
    apk add --no-cache \
      chromium@edge \
      nss@edge

RUN printenv > /app/.env

RUN npm install --production
RUN npx prisma generate
RUN /app/node_modules/next/dist/bin/next build

# Show current folder structure in logs
#RUN ls -al -R
