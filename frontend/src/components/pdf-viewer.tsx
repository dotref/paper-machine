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
    const [uploadedFiles, setUploadedFiles] = useState<{ original: string, stored: string }[]>([]);
    const [isUploadSectionVisible, setIsUploadSectionVisible] = useState(true);
    const [fileToRemove, setFileToRemove] = useState<string | null>(null);

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
                setUploadedFiles(prevFiles => [...prevFiles, { original: data.filename, stored: data.stored_filename }]);

                const uploadEvent = new CustomEvent('fileUploaded', {
                    detail: {
                        filename: data.stored_filename,
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

    const confirmRemoveFile = (filename: string) => {
        setFileToRemove(filename);
    };

    const cancelRemoveFile = () => {
        setFileToRemove(null);
    };

    const removeFile = async (filename: string) => {
        try {
            const response = await fetch(`http://localhost:5000/remove/${filename}`, {
                method: 'DELETE',
            });

            const data = await response.json();

            if (response.ok) {
                setUploadedFiles(prevFiles => prevFiles.filter(file => file.stored !== filename));
                setFileUrl(null);
                setUploadStatus({
                    filename: filename,
                    status: 'success',
                    message: 'File removed successfully'
                });
            } else {
                setUploadStatus({
                    filename: filename,
                    status: 'error',
                    message: data.message || 'Remove failed'
                });
            }
        } catch (error) {
            console.error('Remove error:', error);
            setUploadStatus({
                filename: filename,
                status: 'error',
                message: 'Error removing file'
            });
        } finally {
            setFileToRemove(null);
        }
    };

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

    const toggleUploadSection = () => {
        setIsUploadSectionVisible(!isUploadSectionVisible);
    };

    return (
        <div className="flex flex-col h-full space-y-4">
            <div className="border rounded-lg p-4">
                <div className="flex justify-between items-center">
                    <div className="flex items-center">
                        <h3 className="text-lg font-semibold">Uploaded Files</h3>
                        <button onClick={toggleUploadSection} className="ml-2 text-lg">
                            {isUploadSectionVisible ? '▼' : '▲'}
                        </button>
                    </div>
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
                {isUploadSectionVisible && (
                    <div className="mt-4">
                        {/* Uploaded files list */}
                        {uploadedFiles.length === 0 ? (
                            <p className="text-gray-500">No files uploaded yet.</p>
                        ) : (
                            <ul className="list-disc pl-5">
                                {uploadedFiles.map((file, index) => (
                                    <li key={index} className="flex flex-col">
                                        <div className="flex justify-between items-center">
                                            <span className="cursor-pointer text-blue-500" onClick={() => handleFileClick(file.stored)}>
                                                {file.original}
                                            </span>
                                            <button
                                                className="ml-4 text-red-500"
                                                onClick={() => confirmRemoveFile(file.stored)}
                                            >
                                                Remove
                                            </button>
                                        </div>
                                        {fileToRemove === file.stored && (
                                            <div className="flex justify-end mt-2 space-x-2">
                                                <button
                                                    className="text-red-500"
                                                    onClick={() => removeFile(file.stored)}
                                                >
                                                    Confirm
                                                </button>
                                                <button
                                                    className="text-gray-500"
                                                    onClick={cancelRemoveFile}
                                                >
                                                    Cancel
                                                </button>
                                            </div>
                                        )}
                                    </li>
                                ))}
                            </ul>
                        )}
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