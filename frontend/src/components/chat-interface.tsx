"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useState, useEffect } from "react"

interface Message {
    text: string;
    timestamp: Date;
    sender: string;
    response?: string;
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

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (message.trim()) {
            setIsLoading(true)

            // Add user message
            const userMessage: Message = {
                text: message,
                timestamp: new Date(),
                sender: 'User'
            }
            setMessages(prev => [...prev, userMessage])

            try {
                const response = await fetch('http://localhost:5000/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });

                if (!response.body) {
                    throw new Error('No response body');
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let currentMessage: Message | null = null;

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) {
                        console.log("Stream complete");
                        break;
                    }

                    const decodedValue = decoder.decode(value);
                    console.log("Received chunk:", decodedValue);

                    const messages = decodedValue
                        .split('\n')
                        .filter(line => line.trim())
                        .map(line => {
                            try {
                                return JSON.parse(line);
                            } catch (e) {
                                console.error('Error parsing message:', e);
                                console.log('Problematic line:', line);
                                return null;
                            }
                        })
                        .filter(Boolean);

                    console.log("Parsed messages:", messages);

                    for (const msg of messages) {
                        if (msg.is_continuation && currentMessage) {
                            console.log("Updating existing message with:", msg.message);
                            // Create a new message object to ensure React detects the change
                            const updatedMessage: Message = {
                                ...currentMessage,
                                text: currentMessage.text + ' ' + msg.message
                            };
                            currentMessage = updatedMessage;
                            setMessages(prev => prev.map(m => 
                                m === currentMessage 
                                    ? updatedMessage
                                    : m
                            ));
                        } else {
                            console.log("Creating new message:", msg.message);
                            const agentMessage: Message = {
                                text: msg.message,
                                timestamp: new Date(msg.timestamp),
                                sender: msg.sender,
                                response: 'streaming'
                            }
                            currentMessage = agentMessage;
                            setMessages(prev => [...prev, agentMessage]);
                        }
                    }
                }
            } catch (error) {
                console.error('Error:', error);
                const errorMessage: Message = {
                    text: 'Error connecting to server',
                    timestamp: new Date(),
                    sender: 'System',
                    response: 'error'
                }
                setMessages(prev => [...prev, errorMessage])
            } finally {
                setMessage("")
                setIsLoading(false)
            }
        }
    }

    return (
        <div className="flex flex-col h-[calc(100vh-2rem)] border rounded-lg p-4">
            <div className="flex-grow overflow-y-auto mb-4 space-y-4">
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
                        <div className="mt-1">{msg.text}</div>
                    </div>
                ))}
            </div>
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
    )
}