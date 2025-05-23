import React from "react";
import MenuBar from "./menu-bar";
import { Sidebar } from "./side-bar";

interface MainLayoutProps {
  children: React.ReactNode;
  selectedTab: string;
  onSelectTab: (tab: string) => void;
}

export default function MainLayout({ children, selectedTab, onSelectTab }: MainLayoutProps) {
  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Top navigation bar */}
      <MenuBar />
      
      {/* Main content area with sidebar and children */}
      <div className="flex flex-grow overflow-hidden">
        <div className="h-full" style={{ minHeight: "calc(100vh - 64px)" }}>
          <Sidebar selectedTab={selectedTab} onSelectTab={onSelectTab} />
        </div>
        
        <div className="flex-grow overflow-auto p-4">
          {children}
        </div>
      </div>
    </div>
  );
}