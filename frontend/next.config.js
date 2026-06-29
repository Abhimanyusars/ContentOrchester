/** @type {import('next').NextConfig} */

const RAILWAY_API =
  process.env.API_PROXY_TARGET || "https://contentorchester-production.up.railway.app";

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${RAILWAY_API}/api/v1/:path*`,
      },
      {
        source: "/auth/:path*",
        destination: `${RAILWAY_API}/auth/:path*`,
      },
      {
        source: "/briefs",
        destination: `${RAILWAY_API}/briefs`,
      },
      {
        source: "/briefs/:path*",
        destination: `${RAILWAY_API}/briefs/:path*`,
      },
      {
        source: "/content/:path*",
        destination: `${RAILWAY_API}/content/:path*`,
      },
      {
        source: "/clients/:path*",
        destination: `${RAILWAY_API}/clients/:path*`,
      },
      {
        source: "/ws/:path*",
        destination: `${RAILWAY_API}/ws/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
