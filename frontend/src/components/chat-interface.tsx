"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useState, useEffect } from "react"

interface Message {
    text: string;
    timestamp: Date;
    sender: string;
    response?: string;  // Added to handle backend responses
}

export default function ChatInterface() {
    const [message, setMessage] = useState("")
    const [messages, setMessages] = useState<Message[]>([])
    const [isLoading, setIsLoading] = useState(false)

    useEffect(() => {
        const handleFileUpload = (event: CustomEvent) => {
            const { filename, status, message } = event.detail;
            
            const systemMessage: Message = {
                text: message,
                timestamp: new Date(),
                sender: 'System',
                response: status
            };
            
            setMessages(prev => [...prev, systemMessage]);
        };

        // Add event listener
        window.addEventListener('fileUploaded', handleFileUpload as EventListener);

        // Cleanup
        return () => {
            window.removeEventListener('fileUploaded', handleFileUpload as EventListener);
        };
    }, []);

    // Added: Function to communicate with backend
    const queryBackend = async (userMessage: string) => {
        try {
            const response = await fetch('http://localhost:5000/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: userMessage
                })
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            return await response.json();
        } catch (error) {
            console.error('Error:', error);
            return { message: 'Error connecting to server' };
        }
    }

    // Modified: handleSubmit to include backend communication
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (message.trim()) {
            setIsLoading(true)  // Start loading

            // Add user message
            const userMessage: Message = {
                text: message,
                timestamp: new Date(),
                sender: 'User'
            }
            setMessages(prev => [...prev, userMessage])

            // Get response from backend
            const response = await queryBackend(message)
            
            // Add system response
            const systemMessage: Message = {
                text: response.message || 'No response from server',
                timestamp: new Date(),
                sender: 'System',
                response: response.status
            }
            setMessages(prev => [...prev, systemMessage])

            setMessage("")
            setIsLoading(false)  // End loading
        }
    }

    return (
        <div className="flex flex-col h-[calc(100vh-2rem)] border rounded-lg p-4">
            <div className="flex-grow overflow-y-auto mb-4 space-y-4">
                {messages.map((msg, index) => (
                    <div key={index} className="bg-muted p-3 rounded-lg">
                        <div className="text-sm text-muted-foreground flex justify-between">
                            <span>{msg.sender}</span>
                            <span>{msg.timestamp.toLocaleTimeString()}</span>
                        </div>
                        <div>{msg.text}</div>
                    </div>
                ))}
            </div>
            <form onSubmit={handleSubmit} className="flex gap-2">
                <Input
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    placeholder="Type your message..."
                    className="flex-grow"
                />
                <Button type="submit">Send</Button>
            </form>
        </div>
    )
}