import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "BACII Math",
  description: "Practice BAC II math by handwriting answers, with instant grading and step-by-step explanations.",
};

// The practice canvas implements its own pinch-to-zoom/pan for the drawing
// surface; leaving the page pinch-zoomable lets Safari/Chrome's native gesture
// fight it (a common tablet-drawing-app pitfall — see Procreate/Figma/Excalidraw,
// which all disable native page zoom for the same reason).
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <Navbar />
          <main className="min-h-screen">{children}</main>
        </AuthProvider>
      </body>
    </html>
  );
}
