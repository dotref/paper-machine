"use client"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useState } from "react"

export default function ChatInterface() {
  const [message, setMessage] = useState("")
  const [messages, setMessages] = useState<string[]>([])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (message.trim()) {
      setMessages([...messages, message])
      setMessage("")
    }
  }

  return (
    <div className="flex flex-col h-full border rounded-lg p-4">
      <div className="flex-grow overflow-auto mb-4 space-y-4">
        {messages.map((msg, index) => (
          <div key={index} className="bg-muted p-3 rounded-lg">
            {msg}
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