FROM node:24-alpine

WORKDIR /app

COPY package*.json ./

RUN npm ci

COPY . .

RUN npm run build

ENV PORT=8080
ENV RELAY_MCP_URL=https://re-4f589c522a0645c5b9f2ead60f3e7516.ecs.us-west-2.on.aws/mcp

EXPOSE 8080

CMD ["node", "server/bridge.mjs"]