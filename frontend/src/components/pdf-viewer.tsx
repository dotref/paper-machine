'use client'

import { Button } from "@/components/ui/button"
import { useState } from "react"

interface UploadStatus {
    filename: string;
    status: string;
    message: string;
}

export default function PdfViewer() {
    const [pdfUrl, setPdfUrl] = useState<string | null>(null)
    const [uploadStatus, setUploadStatus] = useState<UploadStatus | null>(null)
    const [isUploading, setIsUploading] = useState(false)

    const uploadToServer = async (file: File) => {
        setIsUploading(true)
        const formData = new FormData()
        formData.append('file', file)

        try {
            const response = await fetch('http://localhost:5000/upload', {
                method: 'POST',
                body: formData,
            })

            const data = await response.json()
            setUploadStatus(data)

            if (response.ok) {
                // Create local URL for PDF preview
                const url = URL.createObjectURL(file)
                setPdfUrl(url)
                
                // Notify chat interface of successful upload (you can customize this message)
                const uploadEvent = new CustomEvent('fileUploaded', {
                    detail: {
                        filename: file.name,
                        status: 'success',
                        message: `Now viewing ${file.name}`
                    }
                })
                window.dispatchEvent(uploadEvent)
            } else {
                // Notify chat interface of failed upload
                const uploadEvent = new CustomEvent('fileUploaded', {
                    detail: {
                        filename: file.name,
                        status: 'error',
                        message: data.message || 'Upload failed'
                    }
                })
                window.dispatchEvent(uploadEvent)
            }
        } catch (error) {
            console.error('Upload error:', error)
            setUploadStatus({
                filename: file.name,
                status: 'error',
                message: 'Upload failed'
            })
            
            // Notify chat interface of error
            const uploadEvent = new CustomEvent('fileUploaded', {
                detail: {
                    filename: file.name,
                    status: 'error',
                    message: 'Error uploading file'
                }
            })
            window.dispatchEvent(uploadEvent)
        } finally {
            setIsUploading(false)
        }
    }

    const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0]
        if (file) {
            await uploadToServer(file)
        }
    }

    return (
        <div className="flex flex-col h-full border rounded-lg p-4">
            <div className="mb-4">
                <input
                    type="file"
                    accept=".pdf,.txt" // txt should be supported too
                    onChange={handleFileChange}
                    className="hidden"
                    id="pdf-upload"
                />
                <label htmlFor="pdf-upload">
                    <Button 
                        variant="outline" 
                        className="w-full" 
                        asChild
                        disabled={isUploading}
                    >
                        <span className="cursor-pointer">
                            {isUploading ? 'Uploading...' : 'Upload PDF/TXT'}
                        </span>
                    </Button>
                </label>
            </div>
            {/* Status message */}
            {uploadStatus && (
                <div className={`mb-4 p-3 rounded ${
                    uploadStatus.status === 'processed' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                }`}>
                    {uploadStatus.message}
                </div>
            )}

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