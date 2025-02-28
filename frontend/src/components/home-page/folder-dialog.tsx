import React, { useEffect, useState } from "react";
import {
  Dialog,
  DialogHeader,
  DialogBody,
  DialogFooter,
  Input,
  Typography,
  Button,
} from "@material-tailwind/react";

interface FolderDialogProps {
  open: boolean;
  handleOpen: () => void;
  folderName: string;
  setFolderName: (name: string) => void;
  createFolder: () => void;
}

export function FolderDialog({
  open,
  handleOpen,
  folderName,
  setFolderName,
  createFolder
}: FolderDialogProps) {
  // State to control animation
  const [isAnimatingIn, setIsAnimatingIn] = useState(false);
  const [isVisible, setIsVisible] = useState(false);

  // Handle animation states when open state changes
  useEffect(() => {
    if (open) {
      setIsVisible(true);
      // Trigger animation in after a tiny delay to ensure visibility is applied first
      setTimeout(() => setIsAnimatingIn(true), 10);
    } else {
      setIsAnimatingIn(false);
      // Wait for animation to complete before hiding
      const timer = setTimeout(() => setIsVisible(false), 300);
      return () => clearTimeout(timer);
    }
  }, [open]);

  if (!isVisible && !open) return null;

  return (
    <div 
      className={`fixed inset-0 bg-black transition-opacity duration-300 ease-in-out flex items-center justify-center z-[9999]
        ${isAnimatingIn ? 'bg-opacity-50' : 'bg-opacity-0'}`} 
      onClick={handleOpen}
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
            New Folder
          </h3>
          <button
            onClick={handleOpen}
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
        
        <div className="p-6">
          <div className="mb-6">
            <label className="block text-gray-700 text-sm font-bold mb-2">
              Folder Name
            </label>
            <input
              type="text"
              value={folderName}
              onChange={(e) => setFolderName(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Enter folder name"
              autoFocus
            />
          </div>
        </div>
        
        <div className="flex justify-end gap-2 p-4 border-t">
          <button
            onClick={handleOpen}
            className="py-2 px-4 rounded-md text-gray-700 hover:bg-gray-100 font-medium transition-colors duration-200"
          >
            Cancel
          </button>
          <button
            onClick={createFolder}
            disabled={!folderName.trim()}
            className={`py-2 px-4 rounded-md text-white font-medium transition-colors duration-200
              ${!folderName.trim() ? 
                'bg-blue-300 cursor-not-allowed' : 
                'bg-blue-600 hover:bg-blue-700'}`}
          >
            Create Folder
          </button>
        </div>
      </div>
    </div>
  );
}