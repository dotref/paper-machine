"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { useRouter } from "next/navigation";

interface User {
    id: number;
    username: string;
    created_at: string;
    last_login: string | null;
}

interface AuthContextType {
    user: User | null;
    token: string | null;
    isAuthenticated: boolean;
    login: (username: string, password: string) => Promise<void>;
    register: (username: string, password: string) => Promise<void>;
    logout: () => void;
    isLoading: boolean;
    error: string | null;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Add this debug function
const debugFetchWithAuth = async (url, options = {}) => {
    const authToken = localStorage.getItem("auth_token");
    const headers = {
        ...options.headers,
        "Authorization": `Bearer ${authToken}`
    };

    console.log(`Debug fetch to ${url}`);
    console.log(`Auth header: Bearer ${authToken?.substring(0, 15)}...`);

    try {
        const response = await fetch(url, {
            ...options,
            headers
        });

        console.log(`Response status: ${response.status}`);
        if (!response.ok) {
            const errorText = await response.text();
            console.error(`Error response: ${errorText}`);
        }

        return response;
    } catch (error) {
        console.error(`Fetch error: ${error.message}`);
        throw error;
    }
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const router = useRouter();

    // Check if token exists in localStorage on initial load
    useEffect(() => {
        const storedToken = localStorage.getItem("auth_token");
        if (storedToken) {
            setToken(storedToken);
            fetchUserProfile(storedToken);
        } else {
            setIsLoading(false);
        }
    }, []);

    // Fetch user profile data when token is available
    const fetchUserProfile = async (authToken: string) => {
        setIsLoading(true);
        try {
            console.log("Fetching user profile with token:", authToken?.substring(0, 15) + "...");

            const response = await fetch("http://localhost:5000/auth/me", {
                headers: {
                    Authorization: `Bearer ${authToken}`,
                },
            });

            console.log("Auth/me response status:", response.status);

            if (response.ok) {
                const userData = await response.json();
                console.log("User data retrieved:", userData);
                setUser(userData);
            } else {
                // Log error details
                const errorText = await response.text();
                console.error("Auth/me error response:", errorText);

                // Token might be invalid or expired
                localStorage.removeItem("auth_token");
                setToken(null);
                setError("Session expired. Please login again.");
            }
        } catch (err) {
            console.error("Error fetching user profile:", err);
            setError("Error fetching user data. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    // Login handler
    const login = async (username: string, password: string) => {
        setIsLoading(true);
        setError(null);

        try {
            // Create form data for OAuth2 password flow
            const formData = new FormData();
            formData.append("username", username);
            formData.append("password", password);

            const response = await fetch("http://localhost:5000/auth/login", {
                method: "POST",
                body: formData,
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Login failed");
            }

            // Store token and fetch user profile
            const { access_token } = data;
            localStorage.setItem("auth_token", access_token);
            setToken(access_token);
            await fetchUserProfile(access_token);

            // Redirect to home page after successful login
            router.push("/home");
        } catch (err: any) {
            console.error("Login error:", err);
            setError(err.message || "Login failed. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    // Register handler
    const register = async (username: string, password: string) => {
        setIsLoading(true);
        setError(null);

        try {
            const response = await fetch("http://localhost:5000/auth/register", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ username, password }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Registration failed");
            }

            // Store token and fetch user profile
            const { access_token } = data;
            localStorage.setItem("auth_token", access_token);
            setToken(access_token);
            await fetchUserProfile(access_token);

            // Redirect to home page after successful registration
            router.push("/home");
        } catch (err: any) {
            console.error("Registration error:", err);
            setError(err.message || "Registration failed. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    // Logout handler
    const logout = () => {
        localStorage.removeItem("auth_token");
        setUser(null);
        setToken(null);
        router.push("/login");
    };

    const value = {
        user,
        token,
        isAuthenticated: !!token,
        login,
        register,
        logout,
        isLoading,
        error,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
}
