import ChatInterface from '@/components/chat-interface'
import PdfViewer from '@/components/pdf-viewer'

export default function Home() {
    return (
        <main className="container mx-auto p-4 h-screen">
            <div className="grid grid-cols-2 gap-4 h-[calc(100vh-2rem)]">
                <ChatInterface />
                <PdfViewer />
            </div>
        </main>
    )
}