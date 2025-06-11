# --- Stage 1: Build the React Application ---

# Use an official Node.js image as the builder.
# 'alpine' is a lightweight version of Linux.
FROM node:18-alpine as builder

# Set the working directory for the build process.
WORKDIR /app

# Copy the package.json and package-lock.json files.
COPY package*.json ./

# Install project dependencies.
RUN npm install

# Copy the rest of the frontend source code.
COPY . .

# Build the React app for production.
# This creates an optimized 'dist' folder with static files.
RUN npm run build


# --- Stage 2: Serve the application with Nginx ---

# Use a lightweight Nginx image for the final container.
FROM nginx:stable-alpine

# Copy the built static files from the 'builder' stage to Nginx's public HTML directory.
COPY --from=builder /app/dist /usr/share/nginx/html

# ADD THIS LINE: Remove the default Nginx config
RUN rm /etc/nginx/conf.d/default.conf

# ADD THIS LINE: Copy our custom Nginx config file into the container
COPY nginx.conf /etc/nginx/conf.d

# Nginx will automatically serve the index.html file from this directory.
# Expose port 80, which is the default HTTP port Nginx listens on.
EXPOSE 80

# The default Nginx command starts the server, so we don't need a CMD here.
