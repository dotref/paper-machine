import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";
import { FolderDialog } from "./folder-dialog";

// Define types for files and folders
interface FileItem {
  name: string;
  type: 'file';
}

interface FolderItem {
  name: string;
  type: 'folder';
  files: FileItem[];
}

type Item = FileItem | FolderItem;

export default function FileManager() {
    const [items, setItems] = useState<Item[]>([]);
    const [currentPath, setCurrentPath] = useState<string[]>([]);
    const [currentItems, setCurrentItems] = useState<Item[]>([]);
    const [fileToRemove, setFileToRemove] = useState<string | null>(null);
    const [statusMessage, setStatusMessage] = useState("");
    const [isUploading, setIsUploading] = useState(false);

    // Ref for hidden file input
    const fileInputRef = React.useRef<HTMLInputElement>(null);

    // Modal state for new folder
    const [isFolderModalOpen, setIsFolderModalOpen] = useState(false);
    const [newFolderName, setNewFolderName] = useState("");

    // Convert backend files to our format when fetched
    useEffect(() => {
        const fetchFiles = async () => {
            try {
                const response = await fetch('http://localhost:5000/files');
                if (!response.ok) throw new Error('Failed to fetch files');
                const data = await response.json();
                
                // Convert string array to FileItem array
                const fileItems: FileItem[] = data.files.map((filename: string) => ({
                    name: filename,
                    type: 'file'
                }));
                
                setItems(fileItems);
            } catch (error) {
                console.error('Error fetching files:', error);
                setStatusMessage("Error loading files");
            }
        };
        fetchFiles();
    }, []);

    // Filter items based on current path
    useEffect(() => {
        if (currentPath.length === 0) {
            // At root level, show all items from root
            setCurrentItems(items);
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
                setCurrentItems(currentFolder.files || []);
            }
        }
    }, [currentPath, items]);

    const handleNewFileClick = () => {
        fileInputRef.current?.click();
    };

    const uploadNewFile = async (file: File) => {
        setIsUploading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('http://localhost:5000/upload', {
                method: 'POST',
                body: formData,
            });
            const data = await response.json();
            if (response.ok) {
                const newFile: FileItem = { 
                    name: data.filename, 
                    type: 'file' 
                };
                
                if (currentPath.length === 0) {
                    // Add file to root
                    setItems(prev => [...prev, newFile]);
                } else {
                    // Add file to current folder
                    const updatedItems = addFileToFolder(items, currentPath, newFile);
                    setItems(updatedItems);
                }
                
                setStatusMessage(`New file "${data.filename}" added.`);
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

    // Helper function to add a file to a nested folder
    const addFileToFolder = (items: Item[], path: string[], newFile: FileItem): Item[] => {
        if (path.length === 0) return [...items, newFile];
        
        return items.map(item => {
            if (item.type === 'folder' && item.name === path[0]) {
                return {
                    ...item,
                    files: path.length === 1 
                        ? [...item.files, newFile] 
                        : addFileToFolder(item.files, path.slice(1), newFile)
                };
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

    // Modal functions for new folder - now only in frontend
    const toggleFolderModal = () => {
        setIsFolderModalOpen(!isFolderModalOpen);
        if (!isFolderModalOpen) {
            setNewFolderName("");
        }
    };

    const createFolder = () => {
        if (!newFolderName.trim()) return;
        
        // Create a new folder
        const newFolder: FolderItem = {
            name: newFolderName,
            type: 'folder',
            files: []
        };

        if (currentPath.length === 0) {
            // Add folder to root
            setItems(prev => [...prev, newFolder]);
        } else {
            // Add folder to the current path
            const updatedItems = addFolderToPath(items, currentPath, newFolder);
            setItems(updatedItems);
        }
        
        setStatusMessage(`Folder "${newFolderName}" created successfully.`);
        setIsFolderModalOpen(false);
    };

    // Helper function to add a folder to a nested path
    const addFolderToPath = (items: Item[], path: string[], newFolder: FolderItem): Item[] => {
        if (path.length === 0) return [...items, newFolder];
        
        return items.map(item => {
            if (item.type === 'folder' && item.name === path[0]) {
                return {
                    ...item,
                    files: path.length === 1 
                        ? [...item.files, newFolder] 
                        : addFolderToPath(item.files, path.slice(1), newFolder)
                };
            }
            return item;
        });
    };

    const confirmRemove = (itemName: string) => {
        setFileToRemove(itemName);
    };

    const cancelRemove = () => {
        setFileToRemove(null);
    };

    const removeItem = async (itemName: string) => {
        const itemToRemove = currentItems.find(item => item.name === itemName);
        
        if (!itemToRemove) {
            setStatusMessage("Item not found");
            return;
        }
        
        if (itemToRemove.type === 'file' && currentPath.length === 0) {
            // Only delete files from backend if they're at the root level
            try {
                const response = await fetch(`http://localhost:5000/remove/${itemName}`, {
                    method: 'DELETE',
                });
                const data = await response.json();
                if (response.ok) {
                    setItems(prev => prev.filter(item => item.name !== itemName));
                    setStatusMessage("File removed successfully");
                } else {
                    setStatusMessage(data.message || "Remove failed");
                }
            } catch (error) {
                console.error('Error removing file:', error);
                setStatusMessage("Error removing file");
            }
        } else {
            // Remove item from the current path
            const updatedItems = removeItemFromPath(items, currentPath, itemName);
            setItems(updatedItems);
            setStatusMessage(`${itemToRemove.type === 'file' ? 'File' : 'Folder'} removed successfully`);
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

    return (
        <div className="p-4">
            {/* Title with breadcrumb navigation */}
            <div className="flex items-center flex-wrap mb-4">
                <h2 className="text-2xl font-bold">
                    <button 
                        onClick={() => setCurrentPath([])}
                        className="hover:text-blue-600 transition-colors duration-200"
                    >
                        Home
                    </button>
                </h2>
                {currentPath.length > 0 && (
                    <div className="flex items-center gap-1 ml-2">
                        <span className="text-gray-500">/</span>
                        {currentPath.map((folder, index) => (
                            <React.Fragment key={index}>
                                <button 
                                    className={`${index === currentPath.length - 1 ? 'font-semibold' : 'hover:text-blue-600'} transition-colors duration-200`}
                                    onClick={() => navigateToPath(index)}
                                >
                                    {folder}
                                </button>
                                {index < currentPath.length - 1 && (
                                    <span className="text-gray-500">/</span>
                                )}
                            </React.Fragment>
                        ))}
                    </div>
                )}
            </div>

            <div className="flex gap-2 mb-4">
                <Button onClick={handleNewFileClick} disabled={isUploading}>
                    New File
                </Button>
                <Button onClick={toggleFolderModal}>
                    New Folder
                </Button>
                <input
                    type="file"
                    accept=".pdf,.txt"
                    ref={fileInputRef}
                    onChange={handleFileChange}
                    className="hidden"
                />
            </div>
            
            {currentItems.length === 0 ? (
                <p className="text-gray-500">
                    {currentPath.length === 0 
                        ? "Your files will appear here." 
                        : "This folder is empty."}
                </p>
            ) : (
                <ul className="space-y-2">
                    {currentItems.map((item, index) => (
                        <li key={index} className="flex flex-col border p-2 rounded-lg">
                            <div className="flex justify-between items-center">
                                {item.type === 'file' ? (
                                    <span
                                        className="text-blue-500 cursor-pointer flex items-center"
                                        onClick={() => {
                                            const event = new CustomEvent('displayFile', {
                                                detail: { filename: encodeURIComponent(item.name), pageLabel: '0' }
                                            });
                                            window.dispatchEvent(event);
                                        }}
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                                            <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                                        </svg>
                                        {item.name}
                                    </span>
                                ) : (
                                    <span 
                                        className="text-yellow-600 cursor-pointer flex items-center"
                                        onClick={() => enterFolder(item.name)}
                                    >
                                        <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                                            <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
                                        </svg>
                                        {item.name}
                                    </span>
                                )}
                                <Button variant="ghost" className="text-red-500" onClick={() => confirmRemove(item.name)}>
                                    Remove
                                </Button>
                            </div>
                            {fileToRemove === item.name && (
                                <div className="flex justify-end space-x-2 mt-2">
                                    <Button variant="destructive" size="sm" onClick={() => removeItem(item.name)}>
                                        Confirm
                                    </Button>
                                    <Button variant="outline" size="sm" onClick={cancelRemove}>
                                        Cancel
                                    </Button>
                                </div>
                            )}
                        </li>
                    ))}
                </ul>
            )}
            
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
