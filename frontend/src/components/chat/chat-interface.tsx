"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useState, useEffect } from "react"
import SelectFilesModal from "./select-files-modal"

interface Source {
    file_name: string;
    page_label: string;
    text: string;
}

interface Message {
    text: string;
    timestamp: Date;
    sender: string;
    response?: string;
    sources?: Source[];
}

// Helper function to filter unique sources
const getUniqueSources = (sources: Source[]): Source[] => {
    const seen = new Set<string>();
    return sources.filter(source => {
        const key = `${source.file_name}-${source.page_label}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });
};

export default function ChatInterface() {
    const [message, setMessage] = useState("")
    const [messages, setMessages] = useState<Message[]>([{
        text: "Hello! I'm Paper Machine. You can upload PDF or TXT files to get started.",
        timestamp: new Date(),
        sender: 'System',
        response: 'success'
    }])
    const [isLoading, setIsLoading] = useState(false)
    const [selectedObjectKeys, setSelectedObjectKeys] = useState<string[]>([]);
    const [isSelectFilesModalOpen, setIsSelectFilesModalOpen] = useState(false)

    useEffect(() => {
        const handleFileUpload = (event: CustomEvent) => {
            const files = event.detail?.files;
        
            if (!Array.isArray(files)) {
                console.warn("Invalid or missing 'files' in event.detail:", event.detail);
                return;
            }
        
            const objectKeys = files.map((f: any) => f.object_key);
            setSelectedObjectKeys(objectKeys); // ✅ store for RAG
        
            const fileNames = files.map((f: any) => f.filename).join(", ");
            const systemMessage: Message = {
                text: `Selected ${files.length} file(s): ${fileNames}`,
                timestamp: new Date(),
                sender: 'System',
                response: 'success'
            };
        
            setMessages(prev => [...prev, systemMessage]);
        };
    
        window.addEventListener('fileUploaded', handleFileUpload as EventListener);
        return () => {
            window.removeEventListener('fileUploaded', handleFileUpload as EventListener);
        };
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!message.trim()) return;
    
        setIsLoading(true);
    
        const userMessage: Message = {
            text: message,
            timestamp: new Date(),
            sender: 'User',
        };
        setMessages(prev => [...prev, userMessage]);
    
        try {
            const response = await fetch('http://localhost:5000/rag/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    Authorization: `Bearer ${localStorage.getItem("auth_token")}`,
                },
                body: JSON.stringify({
                    query: message,
                    object_keys: selectedObjectKeys,
                }),
            });
        
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`HTTP error ${response.status}: ${errorText}`);
            }
        
            let data: any;
            try {
                data = await response.json();
            } catch (jsonErr) {
                console.error("Failed to parse JSON from backend:", jsonErr);
                const fallbackText = await response.text();
                console.error("Raw response body:", fallbackText);
                throw new Error("Backend returned non-JSON response.");
            }
        
            const agentMessage: Message = {
                text: data.response || 'No response from assistant.',
                timestamp: new Date(),
                sender: "Assistant",
                response: "success",
                sources: data.sources ?? [],
            };
        
            setMessages(prev => [...prev, agentMessage]);
        
        } catch (error: any) {
            console.error("RAG chat error:", error);
        
            const errorMessage: Message = {
                text: `Server error: ${error.message || "Unknown error occurred."}`,
                timestamp: new Date(),
                sender: 'System',
                response: 'error'
            };
        
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setMessage("");
            setIsLoading(false);
        }
    };

    return (
        <div className="flex flex-col w-full h-full border rounded-lg">
            <div className="flex justify-between items-center p-4 border-b">
                <h2 className="text-lg font-semibold">Chat</h2>
                <Button 
                    variant="outline"
                    onClick={() => setIsSelectFilesModalOpen(true)}
                    className="text-sm"
                >
                    Select Files
                </Button>
            </div>
            
            {/* Message list - make it flex-grow to take available space */}
            <div className="flex-grow overflow-y-auto p-4 space-y-4">
                {messages.map((msg, index) => (
                    <div 
                        key={index} 
                        className={`p-3 rounded-lg ${
                            msg.sender === 'User' 
                                ? 'bg-blue-100 ml-auto' 
                                : 'bg-gray-100'
                        } max-w-[80%] ${
                            msg.sender === 'User' 
                                ? 'ml-auto' 
                                : 'mr-auto'
                        }`}
                    >
                        <div className="text-sm text-muted-foreground flex justify-between">
                            <span>{msg.sender}</span>
                            <span>{msg.timestamp.toLocaleTimeString()}</span>
                        </div>
                        <div className="mt-1 whitespace-pre-wrap">{msg.text}</div>
                        {msg.sources && msg.sources.length > 0 && (
                            <div className="mt-2">
                                <div className="text-sm text-gray-600 mb-2">Sources:</div>
                                <div className="flex flex-wrap gap-2">
                                    {getUniqueSources(msg.sources).map((source, idx) => (
                                        <Button
                                            key={idx}
                                            variant="outline"
                                            size="sm"
                                            title={source.text}
                                            onClick={() => {
                                                const displayEvent = new CustomEvent('displayFile', {
                                                    detail: {
                                                        filename: source.file_name,
                                                        pageLabel: source.page_label,
                                                    }
                                                });
                                                window.dispatchEvent(displayEvent);
                                            }}
                                        >
                                            {source.file_name} - {source.page_label}
                                        </Button>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                ))}
            </div>
            
            {/* Input area - fixed at bottom */}
            <div className="p-4 border-t">
                <form onSubmit={handleSubmit} className="flex gap-2">
                    <Input
                        value={message}
                        onChange={(e) => setMessage(e.target.value)}
                        placeholder="Type your message..."
                        className="flex-grow"
                        disabled={isLoading}
                    />
                    <Button type="submit" disabled={isLoading}>
                        {isLoading ? 'Sending...' : 'Send'}
                    </Button>
                </form>
            </div>
            
            {/* Files selection modal */}
            <SelectFilesModal 
                isOpen={isSelectFilesModalOpen}
                onClose={() => setIsSelectFilesModalOpen(false)}
            />
        </div>
    )
}