FROM node:22-slim

WORKDIR /workspace/frontend

COPY package.json ./
RUN npm install

EXPOSE 3000

CMD ["npm", "run", "dev"]
