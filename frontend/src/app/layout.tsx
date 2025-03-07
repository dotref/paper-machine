import { AuthProvider } from '@/context/auth-context'
import JwtDebugger from '@/components/auth/jwt-debugger'
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
                    {process.env.NODE_ENV !== 'production' && <JwtDebugger />}
                </AuthProvider>
            </body>
        </html>
    )
}
