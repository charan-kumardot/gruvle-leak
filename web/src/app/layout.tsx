import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const SITE_URL = process.env.NEXT_PUBLIC_APP_URL ?? "http://localhost:3000";
const TITLE = "Gruvle Leak — Find the money your business is losing";
const DESCRIPTION =
  "Gruvle analyzes your business data to uncover unbilled revenue, pricing inconsistencies, missed renewals, invoice mismatches, inventory leakage and other hidden revenue risks. No bank connection required.";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: TITLE, template: "%s — Gruvle Leak" },
  description: DESCRIPTION,
  applicationName: "Gruvle Leak",
  keywords: [
    "revenue leakage", "unbilled revenue", "pricing audit", "invoice reconciliation",
    "renewal risk", "revenue recovery", "SMB finance tools",
  ],
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: "Gruvle Leak",
    title: TITLE,
    description: DESCRIPTION,
    images: [{ url: "/opengraph-image", width: 1200, height: 630, alt: "Gruvle Leak" }],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
    images: ["/opengraph-image"],
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#0b0c0e",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="min-h-screen bg-paper font-sans antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
