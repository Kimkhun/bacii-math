/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  // Lesson animation media (web/public/animations) is immutable per URL: the
  // web appends ?v=<content hash> from the lesson's animation block, so a
  // re-render gets a new URL and students never re-download an unchanged video.
  async headers() {
    return [
      {
        source: "/animations/:path*",
        headers: [{ key: "Cache-Control", value: "public, max-age=31536000, immutable" }],
      },
    ];
  },
};

export default nextConfig;
