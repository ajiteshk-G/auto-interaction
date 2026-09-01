/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: false,
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**" },
      { protocol: "http", hostname: "**" }
    ],
    domains: [
      "images.unsplash.com",
      "via.placeholder.com",
      "www.nexaexperience.com",
      "www.marutisuzuki.com",
      "www.hyundai.com",
      "imgd.aeplcdn.com",
      "www.bmw.in",
      "www.bmw.com"
    ]
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
        source: "/uploads/:path*",
        destination: "http://127.0.0.1:8000/uploads/:path*"
      },
      {
        source: "/ws/:path*",
        destination: "http://127.0.0.1:8000/ws/:path*"
      }
    ];
  }
};

export default nextConfig;
