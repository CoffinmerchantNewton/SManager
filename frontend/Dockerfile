FROM node:22-alpine AS build

WORKDIR /app

RUN corepack enable && corepack prepare pnpm@latest --activate

COPY package.json package-lock.json pnpm-lock.yaml ./

# 优先 npm ci；失败时清理并改用 pnpm
RUN set -e; \
    if npm ci --no-audit --no-fund; then \
      touch /tmp/use-npm; \
    else \
      rm -rf node_modules; \
      pnpm install --frozen-lockfile; \
    fi

COPY . .
ARG VITE_API_URL=/api/v1
ENV VITE_API_URL=${VITE_API_URL}
RUN if [ -f /tmp/use-npm ]; then npm run build; else pnpm run build; fi

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
