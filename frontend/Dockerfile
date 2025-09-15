# === build ===
FROM node:18-alpine AS build
WORKDIR /app

RUN corepack enable && corepack prepare yarn@1.22.22 --activate

COPY package.json yarn.lock ./
RUN yarn install --frozen-lockfile || yarn install

COPY . .
RUN yarn build

FROM alpine:3.19
WORKDIR /opt
COPY --from=build /app/build /opt/build
CMD ["sh","-lc","cp -r /opt/build/* /app/build/ 2>/dev/null || true; tail -f /dev/null"]
