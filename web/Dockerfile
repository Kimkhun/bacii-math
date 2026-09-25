# syntax=docker/dockerfile:1

FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* .npmrc ./

RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund --no-progress

COPY . .

ENV NEXT_TELEMETRY_DISABLED=1

# NOTE: run as a non-root user in the PRODUCTION image only. This Dockerfile is
# used by the dev compose, which bind-mounts host ./web into /app; a non-root
# process then can't write host-owned build artifacts (e.g. .next/), so the
# container crashes on startup. See SECURITY.md #12 for the production guidance.

EXPOSE 3000

CMD ["npm", "run", "dev"]
