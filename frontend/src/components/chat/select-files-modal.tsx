import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { Checkbox } from "@material-tailwind/react";
import { useAuth } from "@/context/auth-context";

interface FileMetadata {
    file_name: string;
    content_type: string;
}

interface FileItem {
    name: string;
    type: 'file';
    object_key: string;
}

interface FolderItem {
    name: string;
    type: 'folder';
    files: (FileItem | FolderItem)[];
    path: string; // Store the full path to this folder
}

type Item = FileItem | FolderItem;

interface FileInfo {
    object_key: string;
    metadata: FileMetadata;
}

interface SelectFilesModalProps {
    isOpen: boolean;
    onClose: () => void;
}


export default function SelectFilesModal({ isOpen, onClose }: SelectFilesModalProps) {
    const { token } = useAuth();
    const [fileStructure, setFileStructure] = useState<Item[]>([]);
    const [selectedFiles, setSelectedFiles] = useState<FileItem[]>([]);
    const [currentPath, setCurrentPath] = useState<string[]>([]);
    const [currentItems, setCurrentItems] = useState<Item[]>([]);
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
            setCurrentPath([]);
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

    // Update current items based on path
    useEffect(() => {
        if (currentPath.length === 0) {
            // At root level
            setCurrentItems(fileStructure);
        } else {
            // Navigate to current path
            let items = [...fileStructure];
            let currentFolder: FolderItem | undefined;
            
            for (const folderName of currentPath) {
                currentFolder = items.find(
                    item => item.type === 'folder' && item.name === folderName
                ) as FolderItem | undefined;
                
                if (!currentFolder) {
                    setCurrentPath([]);
                    return;
                }
                
                items = currentFolder.files;
            }
            
            setCurrentItems(items);
        }
    }, [currentPath, fileStructure]);

    const fetchFiles = async () => {
        setIsLoading(true);
        setError(null);
        
        try {
            // Use the storage/list endpoint to fetch files from MinIO

            if (!token || token === "null") {
              console.error("🚫 No valid token found. Skipping /storage/list request.");
              setError("You must be logged in to view files.");
              setIsLoading(false);
              return;
            }
            
            console.log("📦 Token before /storage/list:", token);
            
            const response = await fetch('http://localhost:5000/storage/list', {
              headers: {
                Authorization: `Bearer ${token}`
              }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to fetch files: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json() as FileInfo[];
            
            // Process the files into a folder structure
            const structure = processFilesIntoFolderStructure(data);
            setFileStructure(structure);
        } catch (error) {
            console.error('Error fetching files:', error);
            setError('Failed to load files. Please try again later.');
            setFileStructure([]);
        } finally {
            setIsLoading(false);
        }
    };

    // Function to process files into a folder structure
    const processFilesIntoFolderStructure = (files: FileInfo[]): Item[] => {
        const root: Item[] = [];
        
        files.forEach(fileInfo => {
            const objectPath = fileInfo.object_key;
            const pathSegments = objectPath.split('/');
            
            if (pathSegments.length === 1) {
                // File is at root level
                root.push({
                    name: fileInfo.metadata.file_name,
                    type: 'file',
                    object_key: fileInfo.object_key
                });
            } else {
                // File is nested in folders
                const fileName = fileInfo.metadata.file_name;
                const folderPath = pathSegments.slice(0, -1);
                
                // Add file to proper folder hierarchy
                addFileToNestedFolder(root, folderPath, {
                    name: fileName,
                    type: 'file',
                    object_key: fileInfo.object_key
                }, '');
            }
        });
        
        return root;
    };
    
    // Helper to add file to nested folder structure
    const addFileToNestedFolder = (items: Item[], folderPath: string[], file: FileItem, parentPath: string) => {
        const currentFolder = folderPath[0];
        const currentFolderPath = parentPath ? `${parentPath}/${currentFolder}` : currentFolder;
        
        // Find or create the folder
        let folder = items.find(
            item => item.type === 'folder' && item.name === currentFolder
        ) as FolderItem | undefined;
        
        if (!folder) {
            folder = {
                name: currentFolder,
                type: 'folder',
                files: [],
                path: currentFolderPath
            };
            items.push(folder);
        }
        
        if (folderPath.length > 1) {
            // Recurse deeper into the folder structure
            addFileToNestedFolder(folder.files, folderPath.slice(1), file, currentFolderPath);
        } else {
            // Add file to this folder
            folder.files.push(file);
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

    // Select all files in current view
    const selectAllCurrentFiles = () => {
        // Get all files in current view (including nested folders)
        const getAllFilesInView = (items: Item[]): FileItem[] => {
            return items.flatMap(item => {
                if (item.type === 'file') {
                    return [item];
                } else {
                    return getAllFilesInView(item.files);
                }
            });
        };
        
        const filesInCurrentView = getAllFilesInView(currentItems);
        
        if (filesInCurrentView.every(file => isFileSelected(file))) {
            // If all files in view are selected, deselect them
            setSelectedFiles(prev => 
                prev.filter(selectedFile => 
                    !filesInCurrentView.some(file => file.object_key === selectedFile.object_key)
                )
            );
        } else {
            // Otherwise, select all files in view that aren't already selected
            setSelectedFiles(prev => {
                const newSelections = filesInCurrentView.filter(
                    file => !prev.some(selectedFile => selectedFile.object_key === file.object_key)
                );
                return [...prev, ...newSelections];
            });
        }
    };

    // Handle folder navigation
    const enterFolder = (folder: FolderItem) => {
        setCurrentPath([...currentPath, folder.name]);
    };

    // Navigate to a specific path level
    const navigateToPath = (index: number) => {
        setCurrentPath(currentPath.slice(0, index + 1));
    };

    // Navigate to root
    const navigateToRoot = () => {
        setCurrentPath([]);
    };

    // Handle viewing selected files
    const viewSelectedFiles = () => {
        if (selectedFiles.length === 0) return;
        
        // Create special event for multiple files
        const event = new CustomEvent('displayMultipleFiles', {
            detail: { 
                files: selectedFiles.map(file => ({
                    filename: file.name,
                    object_key: file.object_key // This is the key that needs proper encoding later
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
                    filename: encodeURIComponent(firstFile.name), // Ensure proper encoding
                    object_key: firstFile.object_key, // Leave as-is, will be encoded in pdf-viewer
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

    // Check if all files in current view are selected
    const areAllFilesInViewSelected = () => {
        const getAllFilesInView = (items: Item[]): FileItem[] => {
            return items.flatMap(item => {
                if (item.type === 'file') {
                    return [item];
                } else {
                    return getAllFilesInView(item.files);
                }
            });
        };
        
        const filesInCurrentView = getAllFilesInView(currentItems);
        return filesInCurrentView.length > 0 && 
               filesInCurrentView.every(file => isFileSelected(file));
    };

    // Count total files in current view
    const countFilesInView = (items: Item[]): number => {
        return items.reduce((count, item) => {
            if (item.type === 'file') {
                return count + 1;
            }
            return count + countFilesInView(item.files);
        }, 0);
    };

    const totalFilesInView = countFilesInView(currentItems);

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

                {/* Breadcrumb navigation */}
                <div className="p-4 border-b">
                    <div className="flex items-center flex-wrap mb-2">
                        <button
                            onClick={navigateToRoot}
                            className="text-blue-600 hover:text-blue-800 font-medium"
                        >
                            Files
                        </button>
                        
                        {currentPath.map((folder, index) => (
                            <React.Fragment key={index}>
                                <span className="mx-2 text-gray-500">/</span>
                                <button
                                    className={`${
                                        index === currentPath.length - 1 
                                            ? 'font-semibold text-gray-700' 
                                            : 'text-blue-600 hover:text-blue-800'
                                    }`}
                                    onClick={() => navigateToPath(index)}
                                >
                                    {folder}
                                </button>
                            </React.Fragment>
                        ))}
                    </div>
                    
                    <div className="flex items-center justify-between">
                        <div className="flex items-center">
                            <Checkbox 
                                id="select-all"
                                checked={areAllFilesInViewSelected()}
                                onChange={selectAllCurrentFiles}
                                color="blue"
                                className="h-4 w-4 mr-2"
                                ripple={false}
                                crossOrigin={undefined}
                            />
                            <label htmlFor="select-all" className="text-sm font-medium cursor-pointer" onClick={selectAllCurrentFiles}>
                                Select All
                            </label>
                        </div>
                        
                        <span className="text-sm text-gray-500">
                            {selectedFiles.length} selected
                        </span>
                    </div>
                </div>

                <div className="max-h-[300px] overflow-y-auto p-2">
                    {isLoading ? (
                        <div className="flex justify-center items-center h-32">
                            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-700"></div>
                        </div>
                    ) : error ? (
                        <div className="flex justify-center items-center h-32 text-red-500">
                            <p>{error}</p>
                        </div>
                    ) : currentItems.length === 0 ? (
                        <div className="flex justify-center items-center h-32">
                            <p className="text-gray-500">This folder is empty</p>
                        </div>
                    ) : (
                        <ul className="space-y-1">
                            {currentItems.map((item, index) => (
                                <li 
                                    key={index} 
                                    className={`rounded-lg transition-colors duration-200 ${
                                        item.type === 'file' && isFileSelected(item as FileItem) 
                                            ? 'bg-blue-50' 
                                            : 'hover:bg-gray-100'
                                    }`}
                                >
                                    {item.type === 'folder' ? (
                                        <div 
                                            className="flex items-center p-2 cursor-pointer"
                                            onClick={() => enterFolder(item as FolderItem)}
                                        >
                                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-yellow-500" viewBox="0 0 20 20" fill="currentColor">
                                                <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
                                            </svg>
                                            <span>{item.name}</span>
                                        </div>
                                    ) : (
                                        <div className="flex items-center p-2">
                                            <Checkbox 
                                                checked={isFileSelected(item as FileItem)}
                                                onChange={() => toggleFileSelection(item as FileItem)}
                                                color="blue"
                                                className="h-4 w-4"
                                                ripple={false}
                                                crossOrigin={undefined}
                                            />
                                            <label 
                                                className="flex items-center ml-2 cursor-pointer flex-grow"
                                                onClick={() => toggleFileSelection(item as FileItem)}
                                            >
                                                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-blue-500" viewBox="0 0 20 20" fill="currentColor">
                                                    <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                                                </svg>
                                                <span className="truncate">{item.name}</span>
                                            </label>
                                        </div>
                                    )}
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
