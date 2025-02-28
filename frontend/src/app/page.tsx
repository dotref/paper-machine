"use client"

import { useState } from "react";
import MainLayout from "@/components/main-layout";
import ChatInterface from "@/components/chat-page/chat-interface";
import PdfViewer from "@/components/chat-page/pdf-viewer";
import FileManager from "@/components/home-page/file-manager";

export default function Home() {
    const [selectedTab, setSelectedTab] = useState("");

    return (
        <MainLayout selectedTab={selectedTab} onSelectTab={setSelectedTab}>
            {selectedTab === "chat" ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-full">
                    <div className="h-full flex overflow-hidden">
                        <ChatInterface />
                    </div>
                    <div className="h-full flex overflow-hidden">
                        <PdfViewer />
                    </div>
                </div>
            ) : (
                <FileManager />
            )}
        </MainLayout>
    );
}