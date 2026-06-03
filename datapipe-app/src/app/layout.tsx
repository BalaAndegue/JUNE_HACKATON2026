import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Providers } from '@/components/layout/Providers'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'DataPipe — Pipeline de données visuels',
  description: 'Créez, automatisez et analysez vos pipelines de données',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body className={`${inter.className} bg-[#0a0a0a] text-gray-200 antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  )
}
