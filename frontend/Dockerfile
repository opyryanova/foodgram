FROM node:21.7.1-alpine
WORKDIR /app

COPY package*.json ./
RUN if [ -f package-lock.json ]; then \
      npm ci --no-audit --no-fund --legacy-peer-deps; \
    else \
      npm install --legacy-peer-deps; \
    fi

COPY . ./
RUN npm run build

CMD ["sh", "-c", "cp -r build result_build"]
