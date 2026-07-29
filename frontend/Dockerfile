# ==============================================================================
# DOCKERFILE FOR FRONTEND (VITE / REACT + TYPESCRIPT)
# ==============================================================================
FROM node:20-alpine

WORKDIR /app

# Copiar configuración del manejador de paquetes
COPY package*.json ./

# Instalar dependencias con caché optimizada
RUN npm install --silent

# Copiar resto del código
COPY . .

EXPOSE 5173

# Iniciar servidor Vite exponiéndolo al exterior para Docker
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
