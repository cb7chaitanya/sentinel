# Build context must be the monorepo root, e.g.
#   docker build -f apps/web/Dockerfile -t sentinel-web .
FROM node:22-slim AS base

FROM base AS deps
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json* ./
RUN npm install

FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web ./
RUN npm run build

FROM base AS runtime
WORKDIR /app
ENV NODE_ENV=production
RUN useradd --create-home --uid 1000 sentinel
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
USER sentinel

EXPOSE 3000
ENV PORT=3000
CMD ["node", "server.js"]
