'use client'

import { Button } from "@/components/ui/button"
import { useState, useEffect } from "react"

interface UploadStatus {
    filename: string;
    status: string;
    message: string;
}

export default function PdfViewer() {
    const [fileUrl, setFileUrl] = useState<string | null>(null)
    const [uploadStatus, setUploadStatus] = useState<UploadStatus | null>(null)
    const [isUploading, setIsUploading] = useState(false)
    const [fileType, setFileType] = useState<'pdf' | 'txt' | null>(null)

    // Function to determine file type
    const getFileType = (filename: string): 'pdf' | 'txt' | null => {
        const extension = filename.split('.').pop()?.toLowerCase();
        if (extension === 'pdf') return 'pdf';
        if (extension === 'txt') return 'txt';
        return null;
    }

    // Function to create PDF viewer URL with page number
    const createPdfViewerUrl = (url: string, pageLabel: string) => {
        // For PDF files, add the page parameter
        return `${url}#page=${parseInt(pageLabel) + 1}`; // Add 1 because PDF viewers use 1-based page numbers
    }

    useEffect(() => {
        const handleDisplayFile = async (event: CustomEvent) => {
            const { filename, pageLabel } = event.detail;
            try {
                const response = await fetch(`http://localhost:5001/uploads/${filename}`);
                if (!response.ok) throw new Error('Failed to fetch file');
                
                const blob = await response.blob();
                const type = getFileType(filename);
                setFileType(type);
                
                let url = URL.createObjectURL(blob);
                
                // For PDFs, add the page parameter
                if (type === 'pdf') {
                    url = createPdfViewerUrl(url, pageLabel);
                }
                
                setFileUrl(url);
                
                setUploadStatus({
                    filename: filename,
                    status: 'processed',
                    message: `Now viewing ${filename}${type === 'pdf' ? ` (page ${parseInt(pageLabel) + 1})` : ''}`
                });
            } catch (error) {
                console.error('Error displaying file:', error);
                setUploadStatus({
                    filename: filename,
                    status: 'error',
                    message: 'Error displaying file'
                });
            }
        };

        window.addEventListener('displayFile', handleDisplayFile as EventListener);
        
        return () => {
            window.removeEventListener('displayFile', handleDisplayFile as EventListener);
            // Cleanup URLs
            if (fileUrl) {
                URL.revokeObjectURL(fileUrl.split('#')[0]); // Remove page parameter before revoking
            }
        };
    }, []);

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
                const url = URL.createObjectURL(file)
                setFileUrl(url)
                setFileType(getFileType(file.name))
                
                const uploadEvent = new CustomEvent('fileUploaded', {
                    detail: {
                        filename: file.name,
                        status: 'success',
                        message: `Now viewing ${file.name}`
                    }
                })
                window.dispatchEvent(uploadEvent)
            } else {
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
                {fileUrl && (
                    fileType === 'txt' ? (
                        <iframe
                            src={fileUrl}
                            className="w-full h-full border-none bg-white"
                            title="Text Viewer"
                        />
                    ) : (
                        <iframe
                            src={fileUrl}
                            className="w-full h-full border-none"
                            title="PDF Viewer"
                        />
                    )
                )}
            </div>
        </div>
    )
}