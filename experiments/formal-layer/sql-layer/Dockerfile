FROM node:20-slim

WORKDIR /app

# Install sqlite3 command-line tool for schema initialization
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Copy package files
COPY package*.json tsconfig.json ./

# Install dependencies
RUN npm install

# Copy application files
COPY . .

# Build TypeScript
RUN npm run build

# Create data directory
RUN mkdir -p /data

EXPOSE 8000

CMD ["npm", "start"]

