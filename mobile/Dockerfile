FROM ghcr.io/cirruslabs/flutter:stable

WORKDIR /app

# Ensure Git safe directory configuration for containerized builds
RUN git config --global --add safe.directory '*'

# Enable Flutter Web platform & disable telemetry
RUN flutter config --enable-web --no-analytics

# Copy pubspec and pre-fetch dependencies for efficient Docker layer caching
COPY pubspec.yaml ./
RUN flutter pub get

# Copy source files
COPY . .

# Expose web dev server port
EXPOSE 3017

# Run Flutter Web Server listening on all interfaces
CMD ["flutter", "run", "-d", "web-server", "--web-port", "3017", "--web-hostname", "0.0.0.0"]
