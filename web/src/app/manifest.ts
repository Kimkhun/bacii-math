import type { MetadataRoute } from "next";

// Next's manifest file convention: this is auto-served at /manifest.webmanifest
// and auto-linked from <head> — no manual <link rel="manifest"> needed.
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "BACII Math Practice",
    short_name: "BACII Math",
    description:
      "Practice BAC II math by handwriting answers, with instant grading and step-by-step explanations.",
    start_url: "/practice",
    display: "standalone",
    background_color: "#f2f1ed",
    theme_color: "#f2f1ed",
    icons: [
      { src: "/manifest-icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/manifest-icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/manifest-icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
    ],
  };
}
