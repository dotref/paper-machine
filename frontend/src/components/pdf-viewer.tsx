'use client'

import { Button } from "@/components/ui/button"
import { useState } from "react"

export default function PdfViewer() {
    const [pdfUrl, setPdfUrl] = useState<string | null>(null)

    const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0]
        if (file) {
            const url = URL.createObjectURL(file)
            setPdfUrl(url)
        }
    }

    return (
        <div className="flex flex-col h-full border rounded-lg p-4">
            <div className="mb-4">
                <input
                    type="file"
                    accept=".pdf"
                    onChange={handleFileChange}
                    className="hidden"
                    id="pdf-upload"
                />
                <label htmlFor="pdf-upload">
                    <Button variant="outline" className="w-full" asChild>
                        <span>Upload PDF</span>
                    </Button>
                </label>
            </div>
            <div className="flex-grow overflow-auto">
                {pdfUrl && (
                    <iframe
                        src={pdfUrl}
                        className="w-full h-full border-none"
                        title="PDF Viewer"
                    />
                )}
            </div>
        </div>
    )
}