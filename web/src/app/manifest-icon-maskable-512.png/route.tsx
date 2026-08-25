import { ImageResponse } from "next/og";

// "Maskable" icons get cropped to a circle/rounded-square/squircle by the OS
// (Android adaptive icons), so the background must be full-bleed (no
// transparency) and the glyph kept inside the ~80%-diameter safe zone —
// smaller and more centered than the plain "any"-purpose 512 icon.
export async function GET() {
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
          fontSize: 220,
          fontWeight: 700,
        }}
      >
        B
      </div>
    ),
    { width: 512, height: 512 }
  );
}
