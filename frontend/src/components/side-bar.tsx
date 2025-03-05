import React from "react";
import {
    Card,
    List,
    ListItem,
    ListItemPrefix
} from "@material-tailwind/react";
import { ChatBubbleLeftEllipsisIcon, HomeIcon } from "@heroicons/react/24/solid";

interface SidebarProps {
    selectedTab: string;
    onSelectTab: (tab: string) => void;
}

export function Sidebar({ selectedTab, onSelectTab }: SidebarProps) {
    return (
        <div className="h-full" style={{ width: '200px', flexShrink: 0 }}>
            <Card
                className="h-full p-4 shadow-xl shadow-blue-gray-900/5"
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
        </div>
    );
}
