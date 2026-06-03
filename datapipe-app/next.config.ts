import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
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
