"use client"

import { useState } from "react";
import { useRouter } from "next/navigation";
import MainLayout from "@/components/main-layout";
import FileManager from "@/components/home-page/file-manager";

export default function HomePage() {
    const [selectedTab, setSelectedTab] = useState("home");
    const router = useRouter();

    const handleTabChange = (tab: string) => {
        if (tab === "chat") {
            router.push("/chat");
        } else {
            setSelectedTab(tab);
        }
    };

    return (
        <MainLayout selectedTab={selectedTab} onSelectTab={handleTabChange}>
            <FileManager />
        </MainLayout>
    );
}
