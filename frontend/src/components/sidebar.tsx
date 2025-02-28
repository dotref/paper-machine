import React from "react";
import {
    Card,
    List,
    ListItem,
    ListItemPrefix
} from "@material-tailwind/react";
import { ChatBubbleLeftEllipsisIcon, HomeIcon } from "@heroicons/react/24/solid";

interface DefaultSidebarWithTabsProps {
    selectedTab: string;
    onSelectTab: (tab: string) => void;
}

export function DefaultSidebarWithTabs({ selectedTab, onSelectTab }: DefaultSidebarWithTabsProps) {
    return (
        <Card
            className="h-[calc(100vh-2rem)] w-full max-w-[20rem] p-4 shadow-xl shadow-blue-gray-900/5"
            placeholder=""
            onPointerEnterCapture={() => { }}
            onPointerLeaveCapture={() => { }}
        >
            <List
                placeholder=""
                onPointerEnterCapture={() => { }}
                onPointerLeaveCapture={() => { }}
            >
                <ListItem
                    onClick={() => onSelectTab("home")}
                    className={`cursor-pointer ${selectedTab === "home" ? "bg-blue-50 font-bold" : ""}`}
                    placeholder=""
                    onPointerEnterCapture={() => { }}
                    onPointerLeaveCapture={() => { }}
                >
                    <ListItemPrefix
                        className="mr-2"
                        placeholder=""
                        onPointerEnterCapture={() => { }}
                        onPointerLeaveCapture={() => { }}
                    >
                        <HomeIcon className="h-5 w-5" />
                    </ListItemPrefix>
                    Home
                </ListItem>
                <ListItem
                    onClick={() => onSelectTab("chat")}
                    className={`cursor-pointer ${selectedTab === "chat" ? "bg-blue-50 font-bold" : ""}`}
                    placeholder=""
                    onPointerEnterCapture={() => { }}
                    onPointerLeaveCapture={() => { }}
                >
                    <ListItemPrefix
                        className="mr-2"
                        placeholder=""
                        onPointerEnterCapture={() => { }}
                        onPointerLeaveCapture={() => { }}
                    >
                        <ChatBubbleLeftEllipsisIcon className="h-5 w-5" />
                    </ListItemPrefix>
                    Chat
                </ListItem>
            </List>
        </Card>
    );
}
