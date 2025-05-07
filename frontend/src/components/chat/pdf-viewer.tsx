'use client'

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import Image from 'next/image'

interface UploadStatus {
    filename: string;
    status: string;
    message: string;
}

interface FileToView {
    filename: string;
    object_key: string;
}

export default function PdfViewer() {
    const [fileUrl, setFileUrl] = useState<string | null>(null)
    const [uploadStatus, setUploadStatus] = useState<UploadStatus | null>(null)
    const [fileType, setFileType] = useState<'pdf' | 'txt' | null>(null)
    const [isUploading, setIsUploading] = useState(false)

    // Multi-file viewing state
    const [multipleFiles, setMultipleFiles] = useState<FileToView[]>([])
    const [currentFileIndex, setCurrentFileIndex] = useState<number>(0)

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
        const handleDisplayMultipleFiles = (event: CustomEvent) => {
            const { files } = event.detail;
            setMultipleFiles(files);
            setCurrentFileIndex(0);
        };

        const handleDisplayFile = async (event: CustomEvent) => {
            const { filename, object_key, pageLabel, isMultiFile, fileIndex, totalFiles } = event.detail;

            // Update multi-file state if provided
            if (isMultiFile && fileIndex !== undefined) {
                setCurrentFileIndex(fileIndex);
            }

            try {
                // Use the storage/serve endpoint when object_key is available
                let url;

                if (object_key) {
                    const encodedObjectKey = encodeURIComponent(object_key);
                    const token = localStorage.getItem("auth_token");
                
                    if (!token) {
                        console.warn("No auth token found. Cannot fetch file.");
                        throw new Error("Missing authentication token");
                    }
                
                    const response = await fetch(`http://localhost:5000/storage/serve/${encodedObjectKey}`, {
                        headers: {
                            Authorization: `Bearer ${token}`,
                        }
                    });
                    
                    if (!response.ok) {
                        console.error(`Error fetching file with status: ${response.status} ${response.statusText}`);
                        throw new Error('Failed to fetch file from storage');
                    }
                    
                    const blob = await response.blob();
                    url = URL.createObjectURL(blob);
                } else {
                    // Fall back to the old method if no object_key
                    const response = await fetch(`http://localhost:5000/uploads/${filename}`);
                    if (!response.ok) throw new Error('Failed to fetch file');

                    const blob = await response.blob();
                    url = URL.createObjectURL(blob);
                }

                const type = getFileType(filename);
                setFileType(type);

                // For PDFs, add the page parameter
                if (type === 'pdf') {
                    url = createPdfViewerUrl(url, pageLabel);
                }

                setFileUrl(url);

                setUploadStatus({
                    filename: decodeURIComponent(filename), // Decode to show readable filename
                    status: 'processed',
                    message: `Now viewing ${decodeURIComponent(filename)}${type === 'pdf' ? ` (page ${parseInt(pageLabel) + 1})` : ''}${
                        isMultiFile ? ` (${fileIndex + 1} of ${totalFiles})` : ''
                    }`
                });
            } catch (error) {
                console.error('Error displaying file:', error);
                setUploadStatus({
                    filename: decodeURIComponent(filename),
                    status: 'error',
                    message: 'Error displaying file'
                });
            }
        };

        window.addEventListener('displayMultipleFiles', handleDisplayMultipleFiles as EventListener);
        window.addEventListener('displayFile', handleDisplayFile as EventListener);

        return () => {
            window.removeEventListener('displayMultipleFiles', handleDisplayMultipleFiles as EventListener);
            window.removeEventListener('displayFile', handleDisplayFile as EventListener);
            // Cleanup URLs
            if (fileUrl) {
                URL.revokeObjectURL(fileUrl.split('#')[0]); // Remove page parameter before revoking
            }
        };
    }, []);

    // Navigate to next file in the multi-file list
    const nextFile = () => {
        if (multipleFiles.length === 0 || currentFileIndex >= multipleFiles.length - 1) return;

        const nextIndex = currentFileIndex + 1;
        const nextFile = multipleFiles[nextIndex];

        const event = new CustomEvent('displayFile', {
            detail: { 
                filename: nextFile.filename, 
                object_key: nextFile.object_key,
                isMultiFile: true,
                fileIndex: nextIndex,
                totalFiles: multipleFiles.length
            }
        });
        window.dispatchEvent(event);
    };

    // Navigate to previous file in the multi-file list
    const prevFile = () => {
        if (multipleFiles.length === 0 || currentFileIndex <= 0) return;

        const prevIndex = currentFileIndex - 1;
        const prevFile = multipleFiles[prevIndex];

        const event = new CustomEvent('displayFile', {
            detail: { 
                filename: prevFile.filename, 
                object_key: prevFile.object_key,
                pageLabel: '0',
                isMultiFile: true,
                fileIndex: prevIndex,
                totalFiles: multipleFiles.length
            }
        });
        window.dispatchEvent(event);
    };

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
        <div className="flex flex-col w-full h-full space-y-4">
            <div className="flex-grow border rounded-lg overflow-auto">
                {fileUrl ? (
                    <div className="flex flex-col h-full">
                        {/* Header with file navigation */}
                        <div className="border-b p-2 flex justify-between items-center">
                            <div className="text-wrap font-semibold truncate max-w-[70%]">
                                {uploadStatus?.filename}
                            </div>

                            {multipleFiles.length > 1 && (
                                <div className="flex items-center space-x-2">
                                    <Button
                                        onClick={prevFile}
                                        disabled={currentFileIndex <= 0}
                                        variant="outline"
                                        size="sm"
                                    >
                                        ← Prev
                                    </Button>
                                    <span className="text-sm text-gray-500">
                                        {currentFileIndex + 1} / {multipleFiles.length}
                                    </span>
                                    <Button
                                        onClick={nextFile}
                                        disabled={currentFileIndex >= multipleFiles.length - 1}
                                        variant="outline"
                                        size="sm"
                                    >
                                        Next →
                                    </Button>
                                </div>
                            )}
                        </div>

                        {/* File viewer */}
                        <div className="flex-grow">
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
                                    style={{ width: '100%' }}
                                >
                                    <p>Unable to display PDF. <a href={fileUrl}>Download</a> instead.</p>
                                </object>
                            ) : (
                                <div className="w-full h-full flex items-center justify-center">
                                    <Image
                                        src={fileUrl}
                                        alt={uploadStatus?.filename || 'Uploaded file'}
                                        width={700}
                                        height={475}
                                        className="max-h-full object-contain"
                                    />
                                </div>
                            )}
                        </div>
                    </div>
                ) : (
                    <div className="h-full flex items-center justify-center text-gray-400">
                        <p>No document selected</p>
                    </div>
                )}
            </div>
        </div>
    )
}