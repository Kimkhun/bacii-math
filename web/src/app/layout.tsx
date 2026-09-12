import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { LanguageProvider } from "@/context/LanguageContext";
import Navbar from "@/components/Navbar";

export const metadata: Metadata = {
  title: "BACII Math",
  description: "Practice BAC II math by handwriting answers, with instant grading and step-by-step explanations.",
  // iOS ignores the web app manifest for "Add to Home Screen" chrome — these
  // are the tags Safari actually reads. `black-translucent` draws the app
  // under the status bar (edge-to-edge), which is why the practice page's
  // fixed bars already pad themselves by `env(safe-area-inset-*)`.
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "BACII Math",
  },
  other: {
    // Next's `appleWebApp.capable` only emits the newer, unprefixed
    // "mobile-web-app-capable" tag — iOS's actual "hide the address bar"
    // switch is still the classic "apple-" prefixed one, so it has to be
    // added explicitly or Safari falls back to normal browser chrome.
    "apple-mobile-web-app-capable": "yes",
  },
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
  themeColor: "#f2f1ed",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        {/*
          Runs before first paint so the document language (and with it font
          selection and screen-reader pronunciation) is the student's own from
          the very first frame. React state still starts at the server-rendered
          "en" and resolves during hydration — doing the same for the rendered
          strings would mean rendering the whole app client-only, which would
          cost the public pages their static HTML.
        */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var l=localStorage.getItem("bacii_lang");if(l==="km"||l==="en"){document.documentElement.lang=l}}catch(e){}`,
          }}
        />
      </head>
      <body>
        <LanguageProvider>
          <AuthProvider>
            <Navbar />
            <main className="min-h-screen">{children}</main>
          </AuthProvider>
        </LanguageProvider>
      </body>
    </html>
  );
}
