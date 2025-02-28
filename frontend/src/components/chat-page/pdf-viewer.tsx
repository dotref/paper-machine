'use client'

import { Button } from "@/components/ui/button"
import { useState, useEffect } from "react"
import Image from 'next/image'

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

                const uploadEvent = new CustomEvent('fileUploaded', {
                    detail: {
                        filename: data.filename,
                        status: 'success',
                        message: `Now viewing ${data.filename}`
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
        const encodedFilename = encodeURIComponent(filename);
        const event = new CustomEvent('displayFile', {
            detail: { filename: encodedFilename, pageLabel: '0' }
        });
        window.dispatchEvent(event);
    };

    return (
        <div className="flex flex-col h-full space-y-4">
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
                        ) : fileType === 'pdf' ? (
                            <object
                                data={fileUrl}
                                type="application/pdf"
                                className="w-full h-full"
                            >
                                <p>Unable to display PDF. <a href={fileUrl}>Download</a> instead.</p>
                            </object>
                        ) : (
                            <Image
                                src={fileUrl}
                                alt={uploadStatus?.filename || 'Uploaded file'}
                                layout="responsive"
                                width={700}
                                height={475}
                                className="max-w-full h-auto"
                            />
                        )}
                    </>
                )}
            </div>
        </div>
    )
}