const backend = process.env.BACKEND_URL || "http://127.0.0.1:8000";
export default {
  output: "standalone",
  experimental: { proxyClientMaxBodySize: "101mb", proxyTimeout: 120000 },
  async rewrites() {
    return [{ source: "/api/:path*", destination: backend + "/:path*" }];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "no-referrer" },
          { key: "Permissions-Policy", value: "camera=(self), microphone=()" },
          { key: "X-Frame-Options", value: "DENY" },
        ],
      },
    ];
  },
};
