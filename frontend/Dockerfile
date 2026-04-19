FROM oven/bun:latest

WORKDIR /app

# Copy dependency files
COPY package.json bun.lock ./

# Install dependencies
RUN bun install

# Copy the rest of the code
COPY . .

# Expose Vite's default port
EXPOSE 5173

# Start the dev server with host 0.0.0.0 to allow access from outside the container
CMD ["bun", "run", "dev", "--host", "0.0.0.0"]
