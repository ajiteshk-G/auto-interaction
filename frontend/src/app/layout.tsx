import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Mahindra Auto — Explore SUVs & Born Electric Origins with Kabir Live Avatar",
  description: "Official Mahindra Virtual Experience Center featuring Live AI Avatar, 3D Co-Browsing, and Real-Time Specs.",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "Mahindra Sales Mobile"
  }
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  themeColor: "#dc2626"
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="manifest" href="/manifest.json" crossOrigin="use-credentials" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
      </head>
      <body className="bg-slate-50 text-slate-900 antialiased selection:bg-red-600 selection:text-white min-h-screen">
        {children}
      </body>
    </html>
  );
}
