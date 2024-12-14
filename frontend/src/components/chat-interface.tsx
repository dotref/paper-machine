"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useState, useEffect } from "react";

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
  return sources.filter((source) => {
    const key = `${source.file_name}-${source.page_label}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
};

export default function ChatInterface() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [token, setToken] = useState<string | null>(
    typeof window !== "undefined" ? localStorage.getItem("invitation_token") : null
  );
  const [isLoggedIn, setIsLoggedIn] = useState(false); // Only true after token validation
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const handleFileUpload = (event: CustomEvent) => {
      const { filename, status, message } = event.detail;

      const systemMessage: Message = {
        text: message,
        timestamp: new Date(),
        sender: "System",
        response: status,
      };

      setMessages((prev) => [...prev, systemMessage]);
    };

    if (typeof window !== "undefined") {
      window.addEventListener("fileUploaded", handleFileUpload as EventListener);

      return () => {
        window.removeEventListener(
          "fileUploaded",
          handleFileUpload as EventListener
        );
      };
    }
  }, []);

  const validateToken = async () => {
    try {
      const response = await fetch("http://localhost:5001/health", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error("Invalid token. Please try again.");
      }

      setIsLoggedIn(true);
      setError(null);
      if (typeof window !== "undefined") {
        localStorage.setItem("invitation_token", token!);
      }
      alert("Login successful! You can now use the application.");
    } catch (err) {
      setError("Invalid token. Please re-enter your Invitation Token.");
      setIsLoggedIn(false);
      setToken("");
      if (typeof window !== "undefined") {
        localStorage.removeItem("invitation_token");
      }
    }
  };

  const handleTokenSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!token) {
      setError("Please enter a valid Invitation Token.");
      return;
    }

    await validateToken();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim()) {
      setIsLoading(true);

      const userMessage: Message = {
        text: message,
        timestamp: new Date(),
        sender: "User",
      };
      setMessages((prev) => [...prev, userMessage]);

      try {
        const apiToken = typeof window !== "undefined" ? localStorage.getItem("invitation_token") : null;
        if (!apiToken) {
          throw new Error("No token found. Please re-enter your Invitation Token.");
        }

        const response = await fetch("http://localhost:5001/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${apiToken}`,
          },
          body: JSON.stringify({ message }),
        });

        if (response.status === 401) {
          setIsLoggedIn(false);
          throw new Error("Invalid token. Please re-enter your Invitation Token.");
        }

        if (!response.body) {
          throw new Error("No response body");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let currentMessage: Message | null = null;

        while (true) {
          const { value, done } = await reader.read();
          if (done) break;

          const decodedValue = decoder.decode(value);

          const parsedMessages = decodedValue
            .split("\n")
            .filter((line) => line.trim())
            .map((line) => JSON.parse(line));

          for (const msg of parsedMessages) {
            if (msg.is_continuation && currentMessage) {
              const updatedMessage: Message = {
                ...currentMessage,
                text: currentMessage.text + " " + msg.message,
              };
              currentMessage = updatedMessage;
              setMessages((prev) =>
                prev.map((m) => (m === currentMessage ? updatedMessage : m))
              );
            } else {
              const agentMessage: Message = {
                text: msg.message,
                timestamp: new Date(msg.timestamp),
                sender: msg.sender,
                response: "streaming",
                sources: msg.sources,
              };
              currentMessage = agentMessage;
              setMessages((prev) => [...prev, agentMessage]);
            }
          }
        }
      } catch (error) {
        const errorMessage: Message = {
          text: error instanceof Error ? error.message : "Network error",
          timestamp: new Date(),
          sender: "System",
          response: "error",
        };
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setMessage("");
        setIsLoading(false);
      }
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)] border rounded-lg p-4">
      {!isLoggedIn && (
        <form onSubmit={handleTokenSubmit} className="mb-4">
          <Input
            value={token || ""}
            onChange={(e) => setToken(e.target.value)}
            placeholder="Enter your Invitation Token"
            className="mb-2"
          />
          <Button type="submit">Submit Token</Button>
          {error && <div className="text-red-500 mt-2">{error}</div>}
        </form>
      )}

      {isLoggedIn && (
        <>
          <div className="flex-grow overflow-y-auto mb-4 space-y-4">
            {messages.map((msg, index) => (
              <div
                key={index}
                className={`p-3 rounded-lg ${
                  msg.sender === "User"
                    ? "bg-blue-100 ml-auto"
                    : "bg-gray-100"
                } max-w-[80%] ${
                  msg.sender === "User" ? "ml-auto" : "mr-auto"
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
                            const displayEvent = new CustomEvent("displayFile", {
                              detail: {
                                filename: source.file_name,
                                pageLabel: source.page_label,
                              },
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
          <form onSubmit={handleSubmit} className="flex gap-2">
            <Input
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Type your message..."
              className="flex-grow"
              disabled={isLoading}
            />
            <Button type="submit" disabled={isLoading}>
              {isLoading ? "Sending..." : "Send"}
            </Button>
          </form>
        </>
      )}
    </div>
  );
}