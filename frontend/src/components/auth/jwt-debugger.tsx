'use client'

import React, { useState, useEffect } from 'react';
import { useAuth } from '@/context/auth-context';

export default function JwtDebugger() {
  const { token } = useAuth();
  const [decodedToken, setDecodedToken] = useState<any>(null);
  const [tokenError, setTokenError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (token) {
      try {
        // Decode JWT (client-side only - no verification)
        const parts = token.split('.');
        if (parts.length !== 3) {
          setTokenError('Invalid token format');
          return;
        }
        
        // Base64 decode the payload
        const payload = JSON.parse(atob(parts[1]));
        setDecodedToken(payload);
      } catch (error) {
        console.error('Error decoding token:', error);
        setTokenError('Error decoding token');
      }
    } else {
      setDecodedToken(null);
    }
  }, [token]);

  if (!token) {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="bg-gray-700 text-white px-3 py-1 rounded text-xs"
      >
        {isOpen ? 'Hide' : 'Show'} JWT Debug
      </button>
      
      {isOpen && (
        <div className="bg-gray-800 text-white p-4 rounded mt-2 max-w-md overflow-auto text-xs">
          <h4 className="font-bold mb-2">JWT Token</h4>
          
          <div className="mb-2">
            <code className="bg-gray-900 p-1 rounded block truncate">
              {token.substring(0, 15)}...{token.substring(token.length - 10)}
            </code>
            <span className="text-xs text-gray-400">Token Length: {token.length}</span>
          </div>
          
          {tokenError ? (
            <div className="text-red-400">{tokenError}</div>
          ) : (
            <>
              <h4 className="font-bold mb-1">Payload</h4>
              <pre className="bg-gray-900 p-2 rounded overflow-auto max-h-40">
                {JSON.stringify(decodedToken, null, 2)}
              </pre>
              
              {decodedToken?.exp && (
                <div className="mt-2 text-xs">
                  <span>Expires: {new Date(decodedToken.exp * 1000).toLocaleString()}</span>
                  <br />
                  <span className={
                    new Date(decodedToken.exp * 1000) > new Date() 
                      ? "text-green-400" 
                      : "text-red-400"
                  }>
                    Status: {new Date(decodedToken.exp * 1000) > new Date() ? "Valid" : "Expired"}
                  </span>
                </div>
              )}
            </>
          )}
          
          <div className="mt-2 text-xs">
            <button 
              onClick={() => {
                navigator.clipboard.writeText(token);
              }}
              className="bg-blue-600 text-white px-2 py-1 rounded mr-2"
            >
              Copy Token
            </button>
            
            <button 
              onClick={async () => {
                try {
                  const response = await fetch('http://localhost:5000/auth/auth-debug', {
                    headers: {
                      Authorization: `Bearer ${token}`
                    }
                  });
                  const data = await response.json();
                  console.log('Auth debug response:', data);
                  alert('Check console for auth debug info');
                } catch (error) {
                  console.error('Auth debug error:', error);
                }
              }}
              className="bg-purple-600 text-white px-2 py-1 rounded"
            >
              Test API Auth
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
