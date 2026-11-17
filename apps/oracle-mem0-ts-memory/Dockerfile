FROM node:22-bookworm-slim AS build

ENV PNPM_HOME=/pnpm
ENV PATH=$PNPM_HOME:$PATH

RUN corepack enable
WORKDIR /app
COPY . .

RUN pnpm install --frozen-lockfile
RUN pnpm build

FROM node:22-bookworm-slim AS runtime

ENV NODE_ENV=production
ENV PORT=8787
WORKDIR /app

COPY --from=build --chown=node:node /app/node_modules ./node_modules
COPY --from=build --chown=node:node /app/services/api/node_modules ./services/api/node_modules
COPY --from=build --chown=node:node /app/services/api/dist ./services/api/dist
COPY --from=build --chown=node:node /app/apps/web/dist ./apps/web/dist

USER node
EXPOSE 8787
CMD ["node", "services/api/dist/index.cjs"]
