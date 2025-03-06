import React from "react";
import { useAuth } from "@/context/auth-context";
import Link from "next/link";

export default function MenuBar() {
  const { logout, user } = useAuth();

  return (
    <div className="flex-shrink-0 z-10 flex justify-between items-center p-4 border-b bg-blue-500 text-white">
      <div className="flex items-center">
        <Link href="/home" className="text-xl font-bold">
          Paper Machine
        </Link>
      </div>
      
      {/* User profile and logout section */}
    <div className="flex items-center gap-4">
      {user && (
        <span className="text-sm text-white">
        Welcome, {user.username}
        </span>
      )}
      
      <button
        onClick={logout}
        className="px-3 py-2 text-sm text-white hover:text-gray-900 hover:bg-gray-100 rounded-md transition-colors"
      >
        Log out
      </button>
    </div>
    </div>
  );
}
