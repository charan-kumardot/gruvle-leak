import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth-context";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gruvle Leak — Find the money your business is losing",
  description:
    "Gruvle analyzes your business data to uncover unbilled revenue, pricing inconsistencies, missed renewals, invoice mismatches, inventory leakage and other hidden revenue risks.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-paper font-sans antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
