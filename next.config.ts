import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Configure webpack to handle better-sqlite3 native binding
  serverExternalPackages: ["better-sqlite3"],
};

export default nextConfig;
