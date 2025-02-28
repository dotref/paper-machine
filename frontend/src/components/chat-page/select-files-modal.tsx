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
    } else {
      setIsAnimatingIn(false);
      // Wait for animation to complete before hiding
      const timer = setTimeout(() => setIsVisible(false), 300);
      return () => clearTimeout(timer);
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
      setFiles([]); // Set to empty array on error
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

        <div className="p-4 max-h-96 overflow-y-auto">
          {isLoading ? (
            <div className="flex justify-center items-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-700"></div>
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
                  className="flex items-center p-2 hover:bg-gray-100 rounded-lg cursor-pointer transition-colors duration-200"
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
