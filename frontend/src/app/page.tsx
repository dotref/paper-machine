"use client"

import { useState, useRef, useEffect } from "react";
import MainLayout from "@/components/main-layout";
import ChatInterface from "@/components/chat-page/chat-interface";
import PdfViewer from "@/components/chat-page/pdf-viewer";
import FileManager from "@/components/home-page/file-manager";

export default function Home() {
    const [selectedTab, setSelectedTab] = useState("home");
    const [isFileDisplayed, setIsFileDisplayed] = useState(false);
    
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

    return (
        <MainLayout selectedTab={selectedTab} onSelectTab={setSelectedTab}>
            {selectedTab === "chat" ? (
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
            ) : (
                <FileManager />
            )}
        </MainLayout>
    );
}