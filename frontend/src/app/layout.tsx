export const metadata = {
    title: 'Paper Machine',
    description: 'Document management and chat interface',
}

import './globals.css'

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en" suppressHydrationWarning>
            <body suppressHydrationWarning>{children}</body>
        </html>
    )
}
