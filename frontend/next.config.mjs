/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: false,
  experimental: {
    allowedDevOrigins: [
      "*.proxy.googlers.com",
      "*.googlers.com",
      "localhost:3000",
      "127.0.0.1:3000"
    ]
  },
  images: {
    domains: ["images.unsplash.com", "via.placeholder.com"]
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Cache-Control", value: "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0" },
          { key: "Pragma", value: "no-cache" },
          { key: "Expires", value: "0" }
        ]
      }
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*"
      },
      {
        source: "/ws/:path*",
        destination: "http://127.0.0.1:8000/ws/:path*"
      }
    ];
  }
};

export default nextConfig;
