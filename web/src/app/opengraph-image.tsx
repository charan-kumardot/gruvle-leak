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
                d="M16 6C11.6 6 8 10.2 8 14.8C8 19.9 12.2 24.4 15.5 26.6C15.8 26.8 16.2 26.8 16.5 26.6C19.8 24.4 24 19.9 24 14.8C24 10.2 20.4 6 16 6Z"
                fill="#C1512E"
              />
              <path
                d="M12.2 15.3L14.8 17.9L19.8 12.4"
                stroke="#FAF9F7"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
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
