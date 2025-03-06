'use client'

import { useState, useEffect } from "react";
import Image from 'next/image';

interface FilePreviewProps {
  selectedFile: {
    name: string;
    object_key?: string;
  } | null;
}

export default function FilePreview({ selectedFile }: FilePreviewProps) {
  const [fileUrl, setFileUrl] = useState<string | null>(null);
  const [fileType, setFileType] = useState<'pdf' | 'txt' | 'image' | 'unsupported' | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Function to determine file type
  const getFileType = (filename: string): 'pdf' | 'txt' | 'image' | 'unsupported' => {
    const extension = filename.split('.').pop()?.toLowerCase();
    if (extension === 'pdf') return 'pdf';
    if (extension === 'txt') return 'txt';
    if (['jpg', 'jpeg', 'png', 'gif', 'webp'].includes(extension || '')) return 'image';
    return 'unsupported';
  };

  // Load file when selected
  useEffect(() => {
    let isMounted = true;
    
    const loadFile = async () => {
      if (!selectedFile || !selectedFile.object_key) {
        setFileUrl(null);
        return;
      }
      
      setIsLoading(true);
      setError(null);
      
      try {
        const encodedObjectKey = encodeURIComponent(selectedFile.object_key);
        const response = await fetch(`http://localhost:5000/storage/serve/${encodedObjectKey}`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch file: ${response.status}`);
        }
        
        const blob = await response.blob();
        
        if (isMounted) {
          const url = URL.createObjectURL(blob);
          setFileUrl(url);
          setFileType(getFileType(selectedFile.name));
        }
      } catch (err) {
        if (isMounted) {
          console.error('Error loading file:', err);
          setError('Failed to load file preview');
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    loadFile();
    
    return () => {
      isMounted = false;
      // Clean up any created object URLs
      if (fileUrl) {
        URL.revokeObjectURL(fileUrl);
      }
    };
  }, [selectedFile]);

  if (!selectedFile) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        <p>Select a file to preview</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center text-red-500">
        <p>{error}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full rounded-lg border overflow-hidden">
      <div className="bg-gray-50 p-3 border-b">
        <h3 className="font-medium truncate pr-10" title={selectedFile.name}>
          {selectedFile.name}
        </h3>
      </div>
      
      <div className="flex-grow overflow-auto">
        {fileUrl ? (
          <>
            {fileType === 'txt' && (
              <iframe
                src={fileUrl}
                className="w-full h-full border-none bg-white"
                title="Text Viewer"
              />
            )}
            
            {fileType === 'pdf' && (
              <object
                data={fileUrl}
                type="application/pdf"
                className="w-full h-full"
              >
                <p className="p-4">Unable to display PDF. <a href={fileUrl} className="text-blue-600 hover:underline" target="_blank" rel="noreferrer">Download</a> instead.</p>
              </object>
            )}
            
            {fileType === 'image' && (
              <div className="w-full h-full flex items-center justify-center p-4">
                <Image
                  src={fileUrl}
                  alt={selectedFile.name}
                  width={700}
                  height={475}
                  className="max-h-full object-contain"
                />
              </div>
            )}
            
            {fileType === 'unsupported' && (
              <div className="flex flex-col items-center justify-center p-4 h-full">
                <div className="text-6xl mb-4">📄</div>
                <p className="text-lg font-medium">{selectedFile.name}</p>
                <p className="text-gray-500 mt-2">Preview not available for this file type</p>
                <a 
                  href={fileUrl} 
                  download={selectedFile.name}
                  className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Download File
                </a>
              </div>
            )}
          </>
        ) : (
          <div className="h-full flex items-center justify-center text-gray-400">
            <p>Preview not available</p>
          </div>
        )}
      </div>
    </div>
  );
}
