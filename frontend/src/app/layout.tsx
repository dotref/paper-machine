import { AuthProvider } from '@/context/auth-context'
import './globals.css'

export const metadata = {
    title: 'Paper Machine',
    description: 'Document management and chat interface',
}

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body suppressHydrationWarning>
                <AuthProvider>
                    {children}
                </AuthProvider>
            </body>
        </html>
    )
}
