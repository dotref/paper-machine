import React from "react";
import MenuBar from "./menu-bar";
import { Sidebar } from "./Sidebar";

interface MainLayoutProps {
	children: React.ReactNode;
	selectedTab: string;
	onSelectTab: (tab: string) => void;
}

export default function MainLayout({ children, selectedTab, onSelectTab }: MainLayoutProps) {
	return (
		<div className="flex flex-col h-screen overflow-hidden">
			{/* Fixed top menu bar */}
			<div className="flex-shrink-0 z-10">
				<MenuBar />
			</div>
			
			{/* Main content area with sidebar */}
			<div className="flex flex-grow overflow-hidden">
				{/* Sidebar with full height */}
				<div className="h-full" style={{ minHeight: "calc(100vh - 64px)" }}>
					<Sidebar selectedTab={selectedTab} onSelectTab={onSelectTab} />
				</div>
				
				{/* Content area with scrolling */}
				<div className="flex-grow overflow-auto p-4">
					{children}
				</div>
			</div>
		</div>
	);
}
