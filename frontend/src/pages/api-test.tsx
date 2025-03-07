"use client";

import React, { useEffect, useState } from 'react';
import { useAuth } from '@/context/auth-context';

export default function APITest() {
  const { token, user } = useAuth();
  const [results, setResults] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(false);
  
  const runTest = async (name: string, url: string, options?: RequestInit) => {
    setLoading(true);
    setResults(prev => ({ ...prev, [name]: { status: 'running' } }));
    
    try {
      const headers = new Headers(options?.headers || {});
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }
      
      const start = Date.now();
      const response = await fetch(url, {
        ...options,
        headers
      });
      const elapsed = Date.now() - start;
      
      let data;
      let responseText = '';
      
      try {
        responseText = await response.text();
        data = JSON.parse(responseText);
      } catch (e) {
        data = { error: 'Failed to parse JSON', text: responseText };
      }
      
      setResults(prev => ({
        ...prev,
        [name]: { 
          status: response.ok ? 'success' : 'error',
          statusCode: response.status,
          elapsed,
          data
        }
      }));
      
    } catch (error: any) {
      setResults(prev => ({
        ...prev,
        [name]: { 
          status: 'error',
          message: error.message,
          error
        }
      }));
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-4">API Test Utility</h1>
      
      <div className="bg-gray-100 p-4 rounded mb-4">
        <h2 className="text-lg font-semibold mb-2">Auth Status</h2>
        <div>Token: {token ? `${token.substring(0, 15)}...` : 'Not logged in'}</div>
        <div>User: {user ? JSON.stringify(user) : 'Not logged in'}</div>
      </div>
      
      <div className="grid grid-cols-2 gap-4 mb-6">
        <button 
          onClick={() => runTest('auth-me', 'http://localhost:5000/auth/me')}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
          disabled={loading}
        >
          Test /auth/me
        </button>
        
        <button 
          onClick={() => runTest('storage-list', 'http://localhost:5000/storage/list')}
          className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
          disabled={loading}
        >
          Test /storage/list
        </button>
        
        <button
          onClick={() => runTest('auth-debug', 'http://localhost:5000/auth/debug-headers')}
          className="px-4 py-2 bg-purple-500 text-white rounded hover:bg-purple-600"
          disabled={loading}
        >
          Test Auth Headers
        </button>
        
        <button
          onClick={() => runTest('ping', 'http://localhost:5000/')}
          className="px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
          disabled={loading}
        >
          Ping API Root
        </button>
      </div>
      
      <div className="mt-6">
        <h2 className="text-lg font-semibold mb-2">Results</h2>
        {Object.entries(results).map(([name, result]) => (
          <div key={name} className="mb-4 border rounded p-4">
            <h3 className="font-medium">
              {name} 
              <span className={`ml-2 px-2 py-1 rounded text-xs ${
                result.status === 'success' ? 'bg-green-100 text-green-800' : 
                result.status === 'error' ? 'bg-red-100 text-red-800' : 
                'bg-yellow-100 text-yellow-800'
              }`}>
                {result.status}
              </span>
              {result.statusCode && <span className="ml-2 text-sm text-gray-500">Status: {result.statusCode}</span>}
              {result.elapsed && <span className="ml-2 text-sm text-gray-500">{result.elapsed}ms</span>}
            </h3>
            <pre className="mt-2 p-2 bg-gray-100 rounded text-xs overflow-auto max-h-40">
              {JSON.stringify(result.data || result, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}
