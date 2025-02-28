"use client"

import { useState } from "react";
import MainLayout from "@/components/main-layout";
import ChatInterface from "@/components/chat-interface";
import PdfViewer from "@/components/pdf-viewer";
import FileManager from "@/components/file-manager";

export default function Home() {
    const [selectedTab, setSelectedTab] = useState("chat");

    return (
        <MainLayout selectedTab={selectedTab} onSelectTab={setSelectedTab}>
            {selectedTab === "chat" ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 h-full">
                    <div className="h-full">
                        <ChatInterface />
                    </div>
                    <div className="h-full">
                        <PdfViewer />
                    </div>
                </div>
            ) : (
                <FileManager />
            )}
        </MainLayout>
    );
}