FROM node:24.15-alpine

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY src ./src
COPY next.config.ts tsconfig.json ./

EXPOSE 3000

CMD ["npm", "run", "dev"]
