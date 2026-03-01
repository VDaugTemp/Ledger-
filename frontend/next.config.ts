import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    // Required for Framer Motion server components compatibility
    optimizePackageImports: ["framer-motion", "lucide-react"],
  },
};

export default nextConfig;
