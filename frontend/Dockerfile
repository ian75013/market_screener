FROM node:20-alpine AS builder

WORKDIR /app

ARG VITE_API_URL=http://localhost:8000/api/v1
ENV VITE_API_URL=${VITE_API_URL}

# Clean slate: remove any existing node_modules and lock files
RUN rm -rf node_modules package-lock.json

# Copy package files
COPY package*.json ./

# Clean npm cache and do fresh install
RUN npm cache clean --force && npm install

# Copy source code and configuration
COPY index.html ./
COPY vite.config.js ./
COPY src ./src
COPY public ./public

# Build the optimized production bundle
RUN npm run build


FROM node:20-alpine

WORKDIR /app

# Install serve to run the static files
RUN npm install -g serve

# Copy only the built dist folder from builder
COPY --from=builder /app/dist ./dist

EXPOSE 3000

# Serve the static files
CMD ["serve", "-s", "dist", "-l", "3000"]
