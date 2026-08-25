import { ImageResponse } from "next/og";

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
          fontSize: 130,
          fontWeight: 700,
        }}
      >
        B
      </div>
    ),
    { width: 192, height: 192 }
  );
}
