# Build the Flutter web release bundle, then serve it statically with nginx.
# (The previous `flutter run -d web-server` debug/DDC setup rendered a blank
# page in the container — the release build bundles CanvasKit locally and is
# served as plain static files, which is reliable.)
FROM ghcr.io/cirruslabs/flutter:stable AS build

WORKDIR /app
RUN git config --global --add safe.directory '*'

# Pre-fetch dependencies for efficient Docker layer caching.
COPY pubspec.yaml ./
RUN flutter pub get

# Copy the source and build the optimized web bundle.
COPY . .
RUN flutter build web --release --no-tree-shake-icons

# --- serve ---
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/build/web /usr/share/nginx/html
EXPOSE 3017
