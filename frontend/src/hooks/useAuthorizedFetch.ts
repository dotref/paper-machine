import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/context/auth-context';

interface FetchOptions extends RequestInit {
  skipAuthRedirect?: boolean;
}

interface UseFetchResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  execute: (url: string, options?: FetchOptions) => Promise<T | null>;
}

export function useAuthorizedFetch<T = any>(): UseFetchResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const { token, logout } = useAuth();
  const router = useRouter();

  const execute = useCallback(
    async (url: string, options: FetchOptions = {}): Promise<T | null> => {
      console.log("Token in useAuthorizedFetch:", token); // 🔍 Add this line
      
      if (!token && !options.skipAuthRedirect) {
        console.error('No token available');
        router.push('/login');
        return null;
      }
      
      setLoading(true);
      setError(null);
      
      try {
        const headers = new Headers(options.headers);
        
        // Add Authorization header if token exists and header isn't already set
        if (token && !headers.has('Authorization')) {
          headers.set('Authorization', `Bearer ${token}`);
        }
        
        console.log(`Fetch request to: ${url}`);
        console.log(`Authorization header included: ${headers.has('Authorization')}`);
        
        const response = await fetch(url, {
          ...options,
          headers
        });
        
        console.log(`Response status: ${response.status}`);
        
        if (response.status === 401 && !options.skipAuthRedirect) {
          console.error('Authentication failed - logging out');
          logout();
          router.push('/login');
          return null;
        }
        
        if (!response.ok) {
          let errorMessage: string;
          try {
            const errorData = await response.json();
            errorMessage = errorData.detail || `Error: ${response.status} ${response.statusText}`;
          } catch (e) {
            errorMessage = `Error: ${response.status} ${response.statusText}`;
          }
          throw new Error(errorMessage);
        }
        
        const responseData = await response.json();
        setData(responseData);
        return responseData;
      } catch (err: any) {
        setError(err.message);
        console.error('Fetch error:', err);
        return null;
      } finally {
        setLoading(false);
      }
    },
    [token, router, logout]
  );
  
  return { data, loading, error, execute };
}
