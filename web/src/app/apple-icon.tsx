import { ImageResponse } from "next/og";

// iOS's own "Add to Home Screen" chrome reads this specific convention
// (served at /apple-icon.png), not the web app manifest's icons array.
export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function AppleIcon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#23272e",
          color: "#f2f1ed",
          fontSize: 110,
          fontWeight: 700,
        }}
      >
        B
      </div>
    ),
    { ...size }
  );
}
