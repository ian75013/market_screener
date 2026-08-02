FROM node:20-alpine AS builder

WORKDIR /app

ARG VITE_API_URL=
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

# `public/` n'existe pas dans ce dépôt et n'y a jamais existé : la ligne
# `COPY public ./public` faisait échouer toute reconstruction avec
# « /public: not found ». L'image qui tourne en production date du 2026-04-16 et
# était donc IRREPRODUCTIBLE — constaté le 2026-08-02 en tentant de la rebâtir.
#
# Vite n'exige pas ce répertoire : il ne sert qu'à copier des fichiers tels quels
# (favicon, robots.txt…) vers la racine du site. On le crée vide pour que l'outil
# le trouve, et il suffira d'y déposer des fichiers le jour où le besoin apparaît.
RUN mkdir -p public

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
