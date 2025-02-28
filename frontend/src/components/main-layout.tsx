import React from "react";
import MenuBar from "./menu-bar";
import { DefaultSidebarWithTabs } from "./sidebar";

interface MainLayoutProps {
	children: React.ReactNode;
	selectedTab: string;
	onSelectTab: (tab: string) => void;
}

export default function MainLayout({ children, selectedTab, onSelectTab }: MainLayoutProps) {
	return (
		<div className="flex flex-col h-screen">
			<MenuBar />
			<div className="flex flex-grow">
				<DefaultSidebarWithTabs selectedTab={selectedTab} onSelectTab={onSelectTab} />
				<div className="flex-grow p-4 overflow-auto">
					{children}
				</div>
			</div>
		</div>
	);
}
