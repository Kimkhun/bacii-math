# syntax=docker/dockerfile:1

FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* .npmrc ./

RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund --no-progress

COPY . .

ENV NEXT_TELEMETRY_DISABLED=1

EXPOSE 3000

CMD ["npm", "run", "dev"]
