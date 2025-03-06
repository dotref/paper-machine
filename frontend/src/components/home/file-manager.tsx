import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { FolderDialog } from "./create-folder-modal";
import FilePreview from "./file-preview";
import { Cross2Icon } from "@radix-ui/react-icons";

// Define types for files and folders
interface FileItem {
    name: string;
    type: 'file';
    object_key?: string; // MinIO object key
}

interface FolderItem {
    name: string;
    type: 'folder';
    files: (FileItem | FolderItem)[];
}

type Item = FileItem | FolderItem;

// API response interfaces
interface FileInfo {
    object_key: string;
    metadata: {
        file_name: string;
        content_type: string;
    };
}

interface UploadResponse {
    message: string;
    fileinfo: FileInfo;
}

export default function FileManager() {
    const [items, setItems] = useState<Item[]>([]);
    const [currentPath, setCurrentPath] = useState<string[]>([]);
    const [currentItems, setCurrentItems] = useState<Item[]>([]);
    const [fileToRemove, setFileToRemove] = useState<string | null>(null);
    const [statusMessage, setStatusMessage] = useState("");
    const [isUploading, setIsUploading] = useState(false);
    const [selectedFile, setSelectedFile] = useState<FileItem | null>(null);

    // Ref for hidden file input
    const fileInputRef = React.useRef<HTMLInputElement>(null);

    // Modal state for new folder
    const [isFolderModalOpen, setIsFolderModalOpen] = useState(false);
    const [newFolderName, setNewFolderName] = useState("");

    // Convert backend files to our format when fetched
    useEffect(() => {
        fetchFiles();
    }, []);

    // Clear selected file when changing folders
    useEffect(() => {
        setSelectedFile(null);
    }, [currentPath]);

    const fetchFiles = async () => {
        try {
            const response = await fetch('http://localhost:5000/storage/list');
            if (!response.ok) throw new Error('Failed to fetch files');
            const data = await response.json() as FileInfo[];

            // Process the flat file list into a folder structure
            const processedItems = processFilesIntoFolderStructure(data);
            setItems(processedItems);
        } catch (error) {
            console.error('Error fetching files:', error);
            setStatusMessage("Error loading files");
        }
    };

    // Updated function to process files into a folder structure
    const processFilesIntoFolderStructure = (files: FileInfo[]): Item[] => {
        const root: Item[] = [];
        const folderPlaceholders: string[] = [];

        // First pass: identify folder placeholders and create an array of folder paths
        files.forEach(fileInfo => {
            if (fileInfo.object_key.endsWith('.folder')) {
                // Extract the folder path and name from the placeholder
                const folderPath = fileInfo.object_key.slice(0, -7); // Remove ".folder"
                folderPlaceholders.push(folderPath);
            }
        });

        // Second pass: process regular files
        files.forEach(fileInfo => {
            // Skip .folder placeholder files when adding files
            if (fileInfo.object_key.endsWith('.folder')) {
                return;
            }

            // Get the path segments from the object_key
            const objectPath = fileInfo.object_key;
            const pathSegments = objectPath.split('/');

            // If no folder path (no slashes), just add file to root
            if (pathSegments.length === 1) {
                root.push({
                    name: fileInfo.metadata.file_name,
                    type: 'file',
                    object_key: fileInfo.object_key
                });
            } else {
                // We have a file inside a folder structure
                const fileName = fileInfo.metadata.file_name;
                const folderPath = pathSegments.slice(0, -1); // All except the last segment

                // Add file to the correct folder in the hierarchy
                addFileToNestedFolder(root, folderPath, {
                    name: fileName,
                    type: 'file',
                    object_key: fileInfo.object_key
                });
            }
        });

        // Third pass: ensure empty folders exist in the structure
        folderPlaceholders.forEach(folderPath => {
            // Skip if it's an empty string
            if (!folderPath) return;

            // Split by slashes to get folder segments
            const pathSegments = folderPath.split('/').filter(segment => segment.length > 0);

            // If we have a folder structure
            if (pathSegments.length > 0) {
                ensureFolderExists(root, pathSegments);
            }
        });

        return root;
    };

    // New helper function to ensure a folder exists in the structure
    const ensureFolderExists = (items: Item[], folderPath: string[]) => {
        // Skip if path is empty
        if (folderPath.length === 0) return;

        const currentFolder = folderPath[0];

        // Find the folder at this level
        let folder = items.find(
            item => item.type === 'folder' && item.name === currentFolder
        ) as FolderItem | undefined;

        // If folder doesn't exist, create it
        if (!folder) {
            folder = {
                name: currentFolder,
                type: 'folder',
                files: []
            };
            items.push(folder);
        }

        // If we have more folders in the path, recurse
        if (folderPath.length > 1) {
            ensureFolderExists(folder.files, folderPath.slice(1));
        }
    };

    // Helper to add file to nested folder structure
    const addFileToNestedFolder = (items: Item[], folderPath: string[], file: FileItem) => {
        // Get the current folder name we're looking for
        const currentFolder = folderPath[0];

        // Find or create the folder at this level
        let folder = items.find(
            item => item.type === 'folder' && item.name === currentFolder
        ) as FolderItem | undefined;

        if (!folder) {
            folder = {
                name: currentFolder,
                type: 'folder',
                files: []
            };
            items.push(folder);
        }

        // If we have more folders in the path, recurse
        if (folderPath.length > 1) {
            addFileToNestedFolder(folder.files, folderPath.slice(1), file);
        } else {
            // We've reached the target folder, add the file
            folder.files.push(file);
        }
    };

    // Filter items based on current path
    useEffect(() => {
        if (currentPath.length === 0) {
            // At root level, show all items from root
            const sortedItems = [...items].sort((a, b) => {
                if (a.type === b.type) return a.name.localeCompare(b.name);
                return a.type === 'folder' ? -1 : 1; // Folders first
            });
            setCurrentItems(sortedItems);
        } else {
            // Find the folder at the current path
            let currentFolder: FolderItem | null = null;
            let tempItems = [...items];

            // Navigate through the path
            for (const folderName of currentPath) {
                const folder = tempItems.find(
                    item => item.type === 'folder' && item.name === folderName
                ) as FolderItem | undefined;

                if (!folder) {
                    // If folder doesn't exist, reset to root
                    setCurrentPath([]);
                    return;
                }

                currentFolder = folder;
                tempItems = currentFolder.files || [];
            }

            if (currentFolder) {
                // Sort the items to display folders first
                const sortedItems = [...currentFolder.files].sort((a, b) => {
                    if (a.type === b.type) return a.name.localeCompare(b.name);
                    return a.type === 'folder' ? -1 : 1; // Folders first
                });
                setCurrentItems(sortedItems);
            }
        }
    }, [currentPath, items]);

    const handleNewFileClick = () => {
        fileInputRef.current?.click();
    };

    const uploadNewFile = async (file: File) => {
        setIsUploading(true);
        setStatusMessage("Uploading file...");
        const formData = new FormData();
        formData.append('file', file);

        // Add current path as a form field if we're in a folder
        if (currentPath.length > 0) {
            formData.append('folder_path', currentPath.join('/'));
        }

        try {
            // Use the storage/upload endpoint
            const response = await fetch('http://localhost:5000/storage/upload', {
                method: 'POST',
                body: formData,
            });

            const data = await response.json() as UploadResponse;

            if (response.ok) {
                const newFile: FileItem = {
                    name: data.fileinfo.metadata.file_name,
                    type: 'file',
                    object_key: data.fileinfo.object_key
                };

                // Handle uploading to current path
                if (currentPath.length === 0) {
                    // Add file to root level
                    setItems(prev => [...prev, newFile]);
                } else {
                    // Add file to the current folder
                    const updatedItems = addFileToFolder(items, currentPath, newFile);
                    setItems(updatedItems);
                }

                setStatusMessage(`File "${data.fileinfo.metadata.file_name}" uploaded successfully.`);

                // Refresh items to ensure we have the latest data
                fetchFiles();
            } else {
                setStatusMessage(data.message || 'Upload failed');
            }
        } catch (error) {
            console.error('Upload error:', error);
            setStatusMessage("Error uploading file");
        } finally {
            setIsUploading(false);
        }
    };

    // Helper function to add a file to a nested folder - improved to handle deep paths better
    const addFileToFolder = (items: Item[], path: string[], newFile: FileItem): Item[] => {
        if (path.length === 0) return [...items, newFile];

        const currentFolder = path[0];
        const remainingPath = path.slice(1);

        return items.map(item => {
            if (item.type === 'folder' && item.name === currentFolder) {
                if (remainingPath.length === 0) {
                    // We've reached the target folder, add the file here
                    return {
                        ...item,
                        files: [...item.files, newFile]
                    };
                } else {
                    // Need to go deeper into the folder structure
                    return {
                        ...item,
                        files: addFileToFolder(item.files, remainingPath, newFile)
                    };
                }
            }
            return item;
        });
    };

    const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            await uploadNewFile(file);
        }
    };

    // Modal functions for new folder
    const toggleFolderModal = () => {
        setIsFolderModalOpen(!isFolderModalOpen);
        if (!isFolderModalOpen) {
            setNewFolderName("");
        }
    };

    // Updated createFolder function to persist folders to backend
    const createFolder = async () => {
        if (!newFolderName.trim()) return;

        setStatusMessage("Creating folder...");

        try {
            // Prepare the folder path (if we're in a sub-folder)
            const folderPath = currentPath.length > 0 ? currentPath.join('/') : "";

            // Call the backend API to create the folder
            const response = await fetch('http://localhost:5000/storage/create_folder', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    folder_name: newFolderName,
                    folder_path: folderPath
                }),
            });

            const data = await response.json();

            if (response.ok) {
                setStatusMessage(`Folder "${newFolderName}" created successfully.`);

                // Refresh the file list to show the new folder
                fetchFiles();
            } else {
                setStatusMessage(data.message || "Failed to create folder");
            }
        } catch (error) {
            console.error('Error creating folder:', error);
            setStatusMessage("Error creating folder");
        }

        setIsFolderModalOpen(false);
    };

    const confirmRemove = (itemName: string) => {
        setFileToRemove(itemName);
    };

    const cancelRemove = () => {
        setFileToRemove(null);
    };

    // Updated removeItem function to handle both files and folders properly in the backend
    const removeItem = async (itemName: string) => {
        const itemToRemove = currentItems.find(item => item.name === itemName);

        if (!itemToRemove) {
            setStatusMessage("Item not found");
            return;
        }

        try {
            if (itemToRemove.type === 'file') {
                // Handle file removal
                if (!itemToRemove.object_key) {
                    throw new Error("File has no object key");
                }

                const response = await fetch(`http://localhost:5000/storage/remove/${itemToRemove.object_key}`, {
                    method: 'DELETE',
                });

                const data = await response.json();

                if (response.ok) {
                    setStatusMessage("File removed successfully");
                } else {
                    setStatusMessage(data.message || "Remove failed");
                    return;
                }
            } else {
                // Handle folder removal with the new endpoint
                // Build the full folder path
                const folderPath = currentPath.length > 0
                    ? `${currentPath.join('/')}/${itemName}`
                    : itemName;

                const response = await fetch('http://localhost:5000/storage/remove_folder', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        folder_path: folderPath
                    }),
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    setStatusMessage(errorData.detail || "Failed to remove folder");
                    return;
                }

                const data = await response.json();
                setStatusMessage(`Folder "${itemName}" and its contents removed successfully`);
            }

            // Update UI state by removing the item
            setItems(prev => {
                if (currentPath.length === 0) {
                    // At root level, just filter out the removed item
                    return prev.filter(item => item.name !== itemName);
                } else {
                    // Remove from nested folder
                    return removeItemFromPath(prev, currentPath, itemName);
                }
            });

            // Refresh the file list to ensure the UI is in sync with the backend
            fetchFiles();

        } catch (error) {
            console.error('Error removing item:', error);
            setStatusMessage(`Error removing ${itemToRemove.type}`);
        }

        setFileToRemove(null);
    };

    // Helper function to remove an item from a nested path
    const removeItemFromPath = (items: Item[], path: string[], itemName: string): Item[] => {
        if (path.length === 0) {
            return items.filter(item => item.name !== itemName);
        }

        return items.map(item => {
            if (item.type === 'folder' && item.name === path[0]) {
                return {
                    ...item,
                    files: path.length === 1
                        ? item.files.filter(file => file.name !== itemName)
                        : removeItemFromPath(item.files, path.slice(1), itemName)
                };
            }
            return item;
        });
    };

    // Handle entering a folder
    const enterFolder = (folderName: string) => {
        setCurrentPath([...currentPath, folderName]);
    };

    // Handle navigating to a specific path level
    const navigateToPath = (index: number) => {
        setCurrentPath(currentPath.slice(0, index + 1));
    };

    // Updated handleFileClick function to toggle preview when clicking the same file
    const handleFileClick = (item: FileItem) => {
        // Skip .folder placeholder files
        if (item.object_key?.endsWith('.folder')) {
            return;
        }

        // Toggle the file selection (close if already selected)
        if (selectedFile && selectedFile.name === item.name) {
            setSelectedFile(null);
        } else {
            // Set the selected file for preview
            setSelectedFile(item);
        }
    };

    // Function to close the preview
    const closePreview = () => {
        setSelectedFile(null);
    };

    return (
        <div className="p-4">
            {/* Title with breadcrumb navigation and action buttons */}
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center flex-wrap">
                    <h2 className="text-2xl font-bold">
                        <button
                            onClick={() => setCurrentPath([])}
                            className="hover:text-blue-600 transition-colors duration-200"
                        >
                            Home
                        </button>
                    </h2>
                    {currentPath.length > 0 && (
                        <div className="text-xl flexitems-center gap-1 ml-2">
                            <span className="text-gray-500">/ </span>
                            {currentPath.map((folder, index) => (
                                <React.Fragment key={index}>
                                    <button
                                        className={`${index === currentPath.length - 1 ? 'font-semibold' : 'hover:text-blue-600'} transition-colors duration-200`}
                                        onClick={() => navigateToPath(index)}
                                    >
                                        {folder}
                                    </button>
                                    {index < currentPath.length - 1 && (
                                        <span className="text-gray-500"> / </span>
                                    )}
                                </React.Fragment>
                            ))}
                        </div>
                    )}
                </div>

                <div className="flex gap-2">
                    <Button
                        onClick={handleNewFileClick}
                        disabled={isUploading}
                        size="md"
                    >
                        {isUploading ? (
                            <>
                                <span className="animate-spin mr-2">⟳</span>
                                Uploading...
                            </>
                        ) : (
                            `Upload${currentPath.length > 0 ? ' to ' + currentPath[currentPath.length - 1] : ''}`
                        )}
                    </Button>
                    <Button onClick={toggleFolderModal} size="md">
                        New Folder{currentPath.length > 0 ? ' in ' + currentPath[currentPath.length - 1] : ''}
                    </Button>
                    <input
                        type="file"
                        accept=".pdf,.txt"
                        ref={fileInputRef}
                        onChange={handleFileChange}
                        className="hidden"
                    />
                </div>
            </div>

            {/* Main content area - conditional rendering based on file selection */}
            <div className="flex gap-6">
                {/* Files and folders list - adjusts width based on selection */}
                <div className={selectedFile ? "w-1/2" : "w-full"}>
                    <ul className="divide-y divide-gray-200 rounded-lg">
                        {currentItems.map((item, index) => (
                            <li 
                                key={index} 
                                className={`rounded-lg pl-3 flex flex-col py-3 hover:bg-gray-50 transition-colors ${
                                    selectedFile && item.type === 'file' && item.name === selectedFile.name ? 'bg-blue-50' : ''
                                }`}
                            >
                                <div 
                                    className="cursor-default flex justify-between items-center w-full" 
                                    onClick={() => item.type === 'file' 
                                        ? handleFileClick(item as FileItem) 
                                        : enterFolder(item.name)
                                    }
                                >
                                    {item.type === 'file' ? (
                                        <span className="text-blue-500 flex items-center min-w-0 overflow-hidden flex-1">
                                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 flex-shrink-0 mr-2" viewBox="0 0 20 20" fill="currentColor">
                                                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                                            </svg>
                                            <span className="truncate" title={item.name}>
                                                {item.name}
                                            </span>
                                        </span>
                                    ) : (
                                        <span className="text-yellow-600 flex items-center min-w-0 overflow-hidden flex-1">
                                            <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 flex-shrink-0 mr-2" viewBox="0 0 20 20" fill="currentColor">
                                                <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
                                            </svg>
                                            <span className="truncate" title={item.name}>
                                                {item.name}
                                            </span>
                                        </span>
                                    )}
                                    <Button 
                                        variant="ghost" 
                                        className="text-red-500 ml-2 flex-shrink-0" 
                                        onClick={(e) => {
                                            e.stopPropagation(); 
                                            confirmRemove(item.name);
                                        }}
                                    >
                                        Remove
                                    </Button>
                                </div>
                                {fileToRemove === item.name && (
                                    <div className="flex justify-end space-x-2 mt-2">
                                        <Button 
                                            variant="destructive" 
                                            size="sm" 
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                removeItem(item.name);
                                            }}
                                        >
                                            Confirm
                                        </Button>
                                        <Button 
                                            variant="outline" 
                                            size="sm" 
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                cancelRemove();
                                            }}
                                        >
                                            Cancel
                                        </Button>
                                    </div>
                                )}
                            </li>
                        ))}
                        {currentItems.length === 0 && (
                            <li className="py-6 text-center text-gray-500">
                                No items in this folder
                            </li>
                        )}
                    </ul>
                </div>

                {/* File Preview Panel - only show when a file is selected */}
                {selectedFile && (
                    <div className="w-1/2 h-[70vh] relative">
                        <Button 
                            variant="ghost" 
                            size="sm" 
                            className="absolute right-2 top-2 z-10 p-1 h-8 w-8"
                            onClick={closePreview}
                        >
                            <Cross2Icon className="h-5 w-5" />
                        </Button>
                        <FilePreview selectedFile={selectedFile} />
                    </div>
                )}
            </div>

            {statusMessage && (
                <div className="mt-4 p-2 border rounded-lg text-center text-sm text-gray-700">
                    {statusMessage}
                </div>
            )}

            {/* Folder creation dialog */}
            <FolderDialog
                open={isFolderModalOpen}
                handleOpen={toggleFolderModal}
                folderName={newFolderName}
                setFolderName={setNewFolderName}
                createFolder={createFolder}
            />
        </div>
    );
}
