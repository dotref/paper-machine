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
                // Add the new file to our items state
                setItems(prev => [
                    ...prev, 
                    { name: data.filename, type: 'file' }
                ]);
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
        
        // Create a new folder in our items state
        const newFolder: FolderItem = {
            name: newFolderName,
            type: 'folder',
            files: []
        };
        
        setItems(prev => [...prev, newFolder]);
        setStatusMessage(`Folder "${newFolderName}" created successfully.`);
        setIsFolderModalOpen(false);
    };

    const confirmRemove = (itemName: string) => {
        setFileToRemove(itemName);
    };

    const cancelRemove = () => {
        setFileToRemove(null);
    };

    const removeItem = async (itemName: string) => {
        // Find the item to remove
        const itemToRemove = items.find(item => item.name === itemName);
        
        if (!itemToRemove) {
            setStatusMessage("Item not found");
            return;
        }
        
        if (itemToRemove.type === 'file') {
            // Delete file from backend
            try {
                const response = await fetch(`http://localhost:5000/remove/${itemName}`, {
                    method: 'DELETE',
                });
                const data = await response.json();
                if (response.ok) {
                    // Remove from our items state
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
            // Just remove folder from frontend state
            setItems(prev => prev.filter(item => item.name !== itemName));
            setStatusMessage("Folder removed successfully");
        }
        
        setFileToRemove(null);
    };

    return (
        <div className="p-4">
            <h2 className="text-2xl font-bold mb-4">Home</h2>
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
            
            {items.length === 0 ? (
                <p className="text-gray-500">Your files will appear here.</p>
            ) : (
                <ul className="space-y-2">
                    {items.map((item, index) => (
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
