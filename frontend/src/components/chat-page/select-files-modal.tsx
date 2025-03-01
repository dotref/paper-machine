import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";

interface FileMetadata {
    file_name: string;
    content_type: string;
}

interface FileItem {
    name: string;
    type: 'file';
    object_key: string;
}

interface FileInfo {
    object_key: string;
    metadata: FileMetadata;
}

interface SelectFilesModalProps {
    isOpen: boolean;
    onClose: () => void;
}

export default function SelectFilesModal({ isOpen, onClose }: SelectFilesModalProps) {
    const [files, setFiles] = useState<FileItem[]>([]);
    const [selectedFiles, setSelectedFiles] = useState<FileItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    // Animation states
    const [isAnimatingIn, setIsAnimatingIn] = useState(false);
    const [isVisible, setIsVisible] = useState(false);

    // Handle animation states when open state changes
    useEffect(() => {
        if (isOpen) {
            setIsVisible(true);
            // Trigger animation in after a tiny delay to ensure visibility is applied first
            setTimeout(() => setIsAnimatingIn(true), 10);
            fetchFiles();
            // Clear selections when modal opens
            setSelectedFiles([]);
        } else {
            setIsAnimatingIn(false);
            // Wait for animation to complete before hiding
            const timer = setTimeout(() => setIsVisible(false), 300);
            return () => clearTimeout(timer);
        }
    }, [isOpen]);

    const fetchFiles = async () => {
        setIsLoading(true);
        setError(null);
        
        try {
            // Use the storage/list endpoint to fetch files from MinIO
            const response = await fetch('http://localhost:5000/storage/list');
            
            if (!response.ok) {
                throw new Error(`Failed to fetch files: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json() as FileInfo[];
            
            // Convert API response to our FileItem format
            const fileItems: FileItem[] = data.map((fileInfo: FileInfo) => ({
                name: fileInfo.metadata.file_name,
                type: 'file',
                object_key: fileInfo.object_key
            }));
            
            setFiles(fileItems);
        } catch (error) {
            console.error('Error fetching files:', error);
            setError('Failed to load files. Please try again later.');
            setFiles([]);
        } finally {
            setIsLoading(false);
        }
    };

    // Toggle selection of a file
    const toggleFileSelection = (file: FileItem) => {
        setSelectedFiles(prev => {
            const isSelected = prev.some(f => f.object_key === file.object_key);
            if (isSelected) {
                return prev.filter(f => f.object_key !== file.object_key);
            } else {
                return [...prev, file];
            }
        });
    };

    // Check if a file is selected
    const isFileSelected = (file: FileItem) => {
        return selectedFiles.some(f => f.object_key === file.object_key);
    };

    // Select all files
    const selectAllFiles = () => {
        if (selectedFiles.length === files.length) {
            // If all are selected, deselect all
            setSelectedFiles([]);
        } else {
            // Otherwise select all
            setSelectedFiles([...files]);
        }
    };

    // Handle viewing selected files
    const viewSelectedFiles = () => {
        if (selectedFiles.length === 0) return;
        
        // Create special event for multiple files
        const event = new CustomEvent('displayMultipleFiles', {
            detail: { 
                files: selectedFiles.map(file => ({
                    filename: file.name,
                    object_key: file.object_key
                }))
            }
        });
        window.dispatchEvent(event);
        
        // Send message to chat about the selected files
        const fileNames = selectedFiles.map(file => file.name).join(", ");
        const uploadEvent = new CustomEvent('fileUploaded', {
            detail: {
                filename: fileNames,
                status: 'success',
                message: `Selected ${selectedFiles.length} file(s): ${fileNames}`
            }
        });
        window.dispatchEvent(uploadEvent);
        
        // Just display the first file immediately
        if (selectedFiles.length > 0) {
            const firstFile = selectedFiles[0];
            const displayEvent = new CustomEvent('displayFile', {
                detail: { 
                    filename: firstFile.name, 
                    object_key: firstFile.object_key,
                    pageLabel: '0',
                    isMultiFile: true,
                    fileIndex: 0,
                    totalFiles: selectedFiles.length
                }
            });
            window.dispatchEvent(displayEvent);
        }
        
        onClose();
    };

    if (!isVisible && !isOpen) return null;

    return (
        <div 
            className={`fixed inset-0 bg-black transition-opacity duration-300 ease-in-out flex items-center justify-center z-[9999]
                ${isAnimatingIn ? 'bg-opacity-50' : 'bg-opacity-0'}`} 
            onClick={onClose}
            aria-modal="true"
            role="dialog"
        >
            {/* Dialog content */}
            <div 
                onClick={(e) => e.stopPropagation()} 
                className={`relative bg-white rounded-lg shadow-xl w-full max-w-md overflow-hidden transition-all duration-300 ease-in-out
                    ${isAnimatingIn ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'}`}
            >
                <div className="flex items-center justify-between p-4 border-b">
                    <h3 className="text-xl font-semibold text-gray-900">
                        Select Files
                    </h3>
                    <button
                        onClick={onClose}
                        className="text-gray-600 hover:text-gray-900 focus:outline-none transition-colors duration-200"
                    >
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            viewBox="0 0 24 24"
                            fill="currentColor"
                            className="h-6 w-6"
                        >
                            <path
                                fillRule="evenodd"
                                d="M5.47 5.47a.75.75 0 011.06 0L12 10.94l5.47-5.47a.75.75 0 111.06 1.06L13.06 12l5.47 5.47a.75.75 0 11-1.06 1.06L12 13.06l-5.47 5.47a.75.75 0 01-1.06-1.06L10.94 12 5.47 6.53a.75.75 0 010-1.06z"
                                clipRule="evenodd"
                            />
                        </svg>
                    </button>
                </div>

                <div className="p-4">
                    <div className="flex items-center mb-4">
                        <Checkbox 
                            id="select-all"
                            checked={files.length > 0 && selectedFiles.length === files.length}
                            onCheckedChange={selectAllFiles}
                        />
                        <label htmlFor="select-all" className="ml-2 text-sm font-medium text-gray-700">
                            Select All
                        </label>
                        <span className="ml-auto text-sm text-gray-500">
                            {selectedFiles.length} of {files.length} selected
                        </span>
                    </div>
                </div>

                <div className="px-4 pb-4 max-h-80 overflow-y-auto">
                    {isLoading ? (
                        <div className="flex justify-center items-center h-32">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-700"></div>
                        </div>
                    ) : error ? (
                        <div className="flex justify-center items-center h-32 text-red-500">
                            <p>{error}</p>
                        </div>
                    ) : files.length === 0 ? (
                        <div className="flex justify-center items-center h-32">
                            <p className="text-gray-500">No files available</p>
                        </div>
                    ) : (
                        <ul className="space-y-2">
                            {files.map((file, index) => (
                                <li 
                                    key={index} 
                                    className={`flex items-center p-2 rounded-lg transition-colors duration-200 ${isFileSelected(file) ? 'bg-blue-50' : 'hover:bg-gray-100'}`}
                                >
                                    <Checkbox 
                                        id={`file-${index}`}
                                        checked={isFileSelected(file)}
                                        onCheckedChange={() => toggleFileSelection(file)}
                                        className="mr-2"
                                    />
                                    <label 
                                        htmlFor={`file-${index}`}
                                        className="flex items-center flex-grow cursor-pointer"
                                        onClick={() => toggleFileSelection(file)}
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-blue-500" viewBox="0 0 20 20" fill="currentColor">
                                            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                                        </svg>
                                        <span>{file.name}</span>
                                    </label>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                <div className="flex justify-between p-4 border-t bg-gray-50">
                    <Button 
                        onClick={fetchFiles} 
                        variant="outline"
                        disabled={isLoading}
                        size="sm"
                    >
                        {isLoading ? 'Refreshing...' : 'Refresh'}
                    </Button>
                    <div className="space-x-2">
                        <Button 
                            onClick={onClose} 
                            variant="outline"
                            size="sm"
                        >
                            Cancel
                        </Button>
                        <Button 
                            onClick={viewSelectedFiles}
                            disabled={selectedFiles.length === 0}
                            size="sm"
                        >
                            View Selected ({selectedFiles.length})
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
