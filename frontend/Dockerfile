FROM node:22-alpine

WORKDIR /app

# Copy package files (assuming you ran `npm create vite@latest . -- --template react`)
COPY package*.json ./
RUN npm install

# Install 3D navigation dependencies
RUN npm install three @react-three/fiber @react-three/drei

COPY . .

EXPOSE 15173

# Run Vite dev server on the custom port
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "15173"]