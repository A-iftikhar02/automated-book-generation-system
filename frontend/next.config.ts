import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server bundle (.next/standalone/server.js) for the Docker image.
  output: "standalone",
  // This app lives in a sub-folder of the repo; pin tracing/Turbopack to it.
  outputFileTracingRoot: __dirname,
  turbopack: { root: __dirname },
  poweredByHeader: false,
};

export default nextConfig;
