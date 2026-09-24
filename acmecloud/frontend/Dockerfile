# Stage 1: Build Acme Store React App
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/templates/default.conf.template

ENV BACKEND_API_URL=http://localhost:8000
ENV CHECKOUT_SERVICE_URL=http://localhost:8001
ENV PORT=80

EXPOSE 80

CMD ["sh", "-c", "envsubst '${BACKEND_API_URL} ${CHECKOUT_SERVICE_URL}' < /etc/nginx/templates/default.conf.template > /etc/nginx/conf.d/default.conf && nginx -g 'daemon off;'"]
