import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Windows-only workaround: `next build`'s static-generation worker pool
  // intermittently fails to spawn child processes on this OS ("spawn
  // UNKNOWN", errno -4094) once the page count grows. Forcing single-
  // threaded generation avoids the spawn entirely; it's slower, not
  // incorrect, and only affects the build step, never runtime behavior.
  experimental: {
    workerThreads: false,
    cpus: 1,
  },
};

export default nextConfig;
