FROM node:21-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
    
FROM alpine:3.19
WORKDIR /opt
COPY --from=build /app/build /opt/build
CMD ["sh", "-c", "cp -r /opt/build/* /app/build/ 2>/dev/null || true; tail -f /dev/null"]
