import React, { useState, useEffect } from 'react';
import { Button } from "@/components/ui/button";

interface FileItem {
  name: string;
  type: 'file';
}

interface SelectFilesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function SelectFilesModal({ isOpen, onClose }: SelectFilesModalProps) {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Fetch files when modal opens
    if (isOpen) {
      fetchFiles();
    }
  }, [isOpen]);

  const fetchFiles = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:5000/files');
      if (!response.ok) throw new Error('Failed to fetch files');
      const data = await response.json();
      
      // Convert string array to FileItem array
      const fileItems: FileItem[] = data.files.map((filename: string) => ({
        name: filename,
        type: 'file'
      }));
      
      setFiles(fileItems);
    } catch (error) {
      console.error('Error fetching files:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileSelect = (fileName: string) => {
    const event = new CustomEvent('displayFile', {
      detail: { filename: encodeURIComponent(fileName), pageLabel: '0' }
    });
    window.dispatchEvent(event);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div 
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[9999]"
      onClick={onClose}
    >
      <div 
        className="bg-white rounded-lg shadow-xl w-full max-w-lg overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-xl font-semibold">Select Files</h3>
          <button
            onClick={onClose}
            className="text-gray-600 hover:text-gray-900 focus:outline-none"
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

        <div className="p-4 max-h-96 overflow-y-auto">
          {isLoading ? (
            <div className="flex justify-center items-center h-32">
              <p>Loading files...</p>
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
                  className="flex items-center p-2 hover:bg-gray-100 rounded-lg cursor-pointer"
                  onClick={() => handleFileSelect(file.name)}
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2 text-blue-500" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
                  </svg>
                  <span>{file.name}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="flex justify-end p-4 border-t bg-gray-50">
          <Button onClick={onClose} variant="outline">
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
