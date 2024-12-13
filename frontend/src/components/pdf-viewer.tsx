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
    const [uploadedFiles, setUploadedFiles] = useState<string[]>([]);

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
                const response = await fetch(`http://localhost:5000/uploads/${filename}`);
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
                setUploadedFiles(prevFiles => [...prevFiles, file.name]);

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

    const handleCloseStatus = () => {
        setUploadStatus(prevStatus => prevStatus ? { ...prevStatus, message: '' } : null);
    };

    const handleFileClick = async (filename: string) => {
        const event = new CustomEvent('displayFile', {
            detail: { filename, pageLabel: '0' }
        });
        window.dispatchEvent(event);
    };

    return (
        <div className="flex flex-col h-full space-y-4">
            <div className="border rounded-lg p-4">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-semibold">Uploaded Files</h3>
                    <input
                        type="file"
                        accept=".pdf,.txt"
                        onChange={handleFileChange}
                        className="hidden"
                        id="pdf-upload"
                    />
                    <label htmlFor="pdf-upload">
                        <Button
                            variant="outline"
                            asChild
                            disabled={isUploading}
                        >
                            <span className="cursor-pointer">
                                {isUploading ? 'Uploading...' : 'Upload PDF/TXT'}
                            </span>
                        </Button>
                    </label>
                </div>
                {/* Uploaded files list */}
                <ul className="list-disc pl-5">
                    {uploadedFiles.map((filename, index) => (
                        <li key={index} className="cursor-pointer text-blue-500" onClick={() => handleFileClick(filename)}>
                            {filename}
                        </li>
                    ))}
                </ul>
                {/* Status message */}
                {uploadStatus && uploadStatus.message && (
                    <div className={`relative border rounded-lg p-4 mt-4 ${uploadStatus.status === 'processed'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                        }`}>
                        <button
                            className="absolute top-0 right-0 mt-2 mr-2 text-lg font-bold"
                            onClick={handleCloseStatus}
                        >
                            &times;
                        </button>
                        {uploadStatus.message}
                    </div>
                )}
            </div>
            <div className="flex-grow border rounded-lg overflow-auto">
                {fileUrl && (
                    <>
                        <div className="border-b p-2 font-semibold">
                            {uploadStatus?.filename}
                        </div>
                        {fileType === 'txt' ? (
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
                        )}
                    </>
                )}
            </div>
        </div>
    )
}