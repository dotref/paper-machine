/**
 * API utility functions with authorization handling
 */

// Base API URL
const API_BASE_URL = 'http://localhost:5000';

/**
 * Get authentication headers with JWT token
 */
export const getAuthHeaders = (contentType = null) => {
  const token = localStorage.getItem('auth_token');
  const headers: Record<string, string> = {
    'Authorization': `Bearer ${token}`
  };
  
  if (contentType) {
    headers['Content-Type'] = contentType;
  }
  
  return headers;
};

/**
 * Perform an authenticated GET request
 */
export const authGet = async (endpoint: string) => {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'GET',
    headers: getAuthHeaders()
  });
  
  if (!response.ok) {
    const error = await handleErrorResponse(response);
    throw error;
  }
  
  return response.json();
};

/**
 * Perform an authenticated POST request with JSON body
 */
export const authPost = async (endpoint: string, data: any) => {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: getAuthHeaders('application/json'),
    body: JSON.stringify(data)
  });
  
  if (!response.ok) {
    const error = await handleErrorResponse(response);
    throw error;
  }
  
  return response.json();
};

/**
 * Perform an authenticated POST request with FormData
 */
export const authFormPost = async (endpoint: string, formData: FormData) => {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: getAuthHeaders(), // No Content-Type for FormData
    body: formData
  });
  
  if (!response.ok) {
    const error = await handleErrorResponse(response);
    throw error;
  }
  
  return response.json();
};

/**
 * Perform an authenticated DELETE request
 */
export const authDelete = async (endpoint: string) => {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  
  if (!response.ok) {
    const error = await handleErrorResponse(response);
    throw error;
  }
  
  return response.json();
};

/**
 * Handle error responses
 */
const handleErrorResponse = async (response: Response) => {
  let errorMessage = `Error ${response.status}`;
  try {
    const errorData = await response.json();
    errorMessage = errorData.detail || errorMessage;
  } catch (e) {
    // If error isn't JSON, try to get text
    try {
      const errorText = await response.text();
      if (errorText) {
        errorMessage = errorText;
      }
    } catch (textError) {
      // Fallback to status message
    }
  }
  
  console.error(`API Error: ${errorMessage}`);
  return new Error(errorMessage);
};

/**
 * Test authentication status
 * Returns true if token is valid
 */
export const testAuth = async () => {
  try {
    await authGet('/auth/me');
    return true;
  } catch (error) {
    console.error('Auth test failed:', error);
    return false;
  }
};

/**
 * Log detailed API information
 */
export const logAPIRequest = (method: string, url: string, headers: any, body?: any) => {
  console.group(`API Request: ${method} ${url}`);
  console.log('Headers:', headers);
  if (body) {
    console.log('Body:', body);
  }
  console.groupEnd();
};

/**
 * Log API response information
 */
export const logAPIResponse = async (response: Response, url: string) => {
  console.group(`API Response: ${url}`);
  console.log('Status:', response.status, response.statusText);
  try {
    // Clone the response to avoid consuming it
    const cloned = response.clone();
    const data = await cloned.text();
    console.log('Response:', data.length > 1000 ? data.substring(0, 1000) + '...' : data);
  } catch (e) {
    console.log('Could not log response body');
  }
  console.groupEnd();
};

/**
 * Create an authenticated URL for file download/viewing
 */
export const getAuthenticatedFileUrl = (objectKey: string): string => {
  const token = localStorage.getItem('auth_token');
  
  // Encode the object key for safe URL inclusion
  const encodedKey = encodeURIComponent(objectKey);
  const url = `${API_BASE_URL}/storage/serve/${encodedKey}`;
  
  return url;
};

/**
 * Download a file with authentication
 */
export const downloadFile = async (objectKey: string, filename?: string): Promise<Blob> => {
  const token = localStorage.getItem('auth_token');
  
  // Encode the object key for safe URL inclusion
  const encodedKey = encodeURIComponent(objectKey);
  const url = `${API_BASE_URL}/storage/serve/${encodedKey}`;
  
  const response = await fetch(url, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  if (!response.ok) {
    const error = await handleErrorResponse(response);
    throw error;
  }
  
  return response.blob();
};
