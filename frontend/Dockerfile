FROM node:20-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./

RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund

COPY . .
RUN npm run build

FROM alpine:3.19
WORKDIR /opt
COPY --from=build /app/build /opt/build
CMD ["sh", "-c", "cp -r /opt/build/* /app/build/ 2>/dev/null || true; tail -f /dev/null"]
