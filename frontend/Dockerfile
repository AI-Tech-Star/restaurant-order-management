# syntax=docker/dockerfile:1

FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci

COPY . .

RUN npm run build

FROM node:20-alpine AS runtime

RUN npm install -g serve@14.2.1 && npm cache clean --force

WORKDIR /app

COPY --from=builder /app/dist ./dist

EXPOSE 80

CMD ["serve", "-s", "dist", "-l", "80"]