import type { NextConfig } from "next";

// Static export for GitHub Pages, served from the /about-me sub-path.
const nextConfig: NextConfig = {
  output: "export",
  basePath: "/about-me",
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
