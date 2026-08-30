import { ImageResponse } from "next/og";

export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          backgroundColor: "#faf9f7",
          backgroundImage:
            "linear-gradient(to right, #e6e7ea 1px, transparent 1px), linear-gradient(to bottom, #e6e7ea 1px, transparent 1px)",
          backgroundSize: "56px 56px",
          padding: "72px",
          fontFamily: "sans-serif",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 14,
              backgroundColor: "#0b0c0e",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <svg width="30" height="30" viewBox="0 0 32 32" fill="none">
              <path
                d="M10.21,22.89 A9,9 0 1 1 21.79,22.89"
                stroke="#FAF9F7"
                strokeWidth="2.6"
                strokeLinecap="round"
                fill="none"
              />
              <circle cx="16" cy="25" r="2.3" fill="#C1512E" />
            </svg>
          </div>
          <span style={{ fontSize: 30, fontWeight: 600, color: "#0b0c0e" }}>Gruvle Leak</span>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 980 }}>
          <div style={{ fontSize: 62, fontWeight: 600, color: "#0b0c0e", lineHeight: 1.1, letterSpacing: -1 }}>
            Find the money your business is losing.
          </div>
          <div style={{ fontSize: 26, color: "#5c6169", lineHeight: 1.4 }}>
            Evidence-backed revenue leak detection — no bank connection required.
          </div>
        </div>

        <div style={{ display: "flex", gap: 12 }}>
          {["Unbilled revenue", "Pricing gaps", "Invoice mismatches", "Renewal risk"].map((label) => (
            <div
              key={label}
              style={{
                display: "flex",
                padding: "10px 18px",
                borderRadius: 999,
                border: "1px solid #c9ccd1",
                backgroundColor: "#ffffff",
                fontSize: 18,
                color: "#43474f",
              }}
            >
              {label}
            </div>
          ))}
        </div>
      </div>
    ),
    { ...size }
  );
}
