FROM oven/bun:1.3-alpine

WORKDIR /app

# Static deps only — no node_modules to install. Copy what we need to run.
COPY package.json server.js ./
COPY public ./public

ENV NODE_ENV=production
EXPOSE 3000

CMD ["bun", "run", "server.js"]
