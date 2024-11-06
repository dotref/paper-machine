"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useState } from "react"

interface Message {
    text: string;
    timestamp: Date;
    sender: string;
}

export default function ChatInterface() {
    const [message, setMessage] = useState("")
    const [messages, setMessages] = useState<Message[]>([])

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault()
        if (message.trim()) {
            setMessages([...messages, {
                text: message,
                timestamp: new Date(),
                sender: 'User'
            }])
            setMessage("")
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