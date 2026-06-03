import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  // Slim, self-contained server output for Docker (next/standalone).
  output: 'standalone',
  // Allow cross-origin requests from the backend in dev
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [{ key: 'Access-Control-Allow-Origin', value: '*' }],
      },
    ]
  },
}

export default nextConfig
