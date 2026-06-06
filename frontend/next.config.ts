import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async redirects() {
    return [{ source: "/review", destination: "/profile", permanent: true }];
  },
};

export default nextConfig;
