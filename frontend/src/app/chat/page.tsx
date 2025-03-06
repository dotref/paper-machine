"use client"

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import MainLayout from "@/components/main-layout";
import ChatInterface from "@/components/chat-page/chat-interface";
import PdfViewer from "@/components/chat-page/pdf-viewer";

export default function ChatPage() {
    const [selectedTab, setSelectedTab] = useState("chat");
    const [isFileDisplayed, setIsFileDisplayed] = useState(false);
    const router = useRouter();

    // Reference for layout dimensions
    const chatColumnRef = useRef<HTMLDivElement>(null);
    const pdfColumnRef = useRef<HTMLDivElement>(null);

    // Setup event listeners for file display
    useEffect(() => {
        const handleDisplayFile = () => setIsFileDisplayed(true);

        window.addEventListener('displayFile', handleDisplayFile);

        return () => {
            window.removeEventListener('displayFile', handleDisplayFile);
        };
    }, []);

    const handleTabChange = (tab: string) => {
        if (tab === "home") {
            router.push("/home");
        } else {
            setSelectedTab(tab);
        }
    };

    return (
        <MainLayout selectedTab={selectedTab} onSelectTab={handleTabChange}>
            <div className="grid grid-cols-2 gap-4 h-full" style={{ gridTemplateColumns: "1fr 1fr" }}>
                <div
                    ref={chatColumnRef}
                    className="h-full flex overflow-hidden"
                >
                    <ChatInterface />
                </div>
                <div
                    ref={pdfColumnRef}
                >
                    <PdfViewer />
                </div>
            </div>
        </MainLayout>
    );
}
