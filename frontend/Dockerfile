FROM node:18-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 3000

# Start the Next.js application in dev mode
CMD ["npm", "run", "dev"]
