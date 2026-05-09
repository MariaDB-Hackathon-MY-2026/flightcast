/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  // The web container talks to the api container via internal hostname.
  // Default to the docker-compose service name `api`; override at build time
  // with API_BASE_INTERNAL=http://localhost:8000 for `npm run dev` outside
  // Docker. Browser-facing requests use the rewritten /api/* path.
  async rewrites() {
    const dest = process.env.API_BASE_INTERNAL || "http://api:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${dest}/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
