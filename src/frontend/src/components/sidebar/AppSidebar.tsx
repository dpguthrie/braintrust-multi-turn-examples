import { MessageSquare, Plus } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarSeparator,
} from "@/components/ui/sidebar";

type AppSidebarProps = {
  onNewChat: () => void;
};

export function AppSidebar({ onNewChat }: AppSidebarProps) {
  return (
    <Sidebar collapsible="icon" variant="inset">
      <SidebarHeader>
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold">Rev Demo</span>
          <Button className="h-8 w-8" onClick={onNewChat} size="icon">
            <Plus className="size-4" />
          </Button>
        </div>
      </SidebarHeader>
      <SidebarSeparator />
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Chats</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton isActive>
                  <MessageSquare className="size-4" />
                  <span>Current chat</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <div className="text-xs text-muted-foreground">
          Braintrust + LangGraph
        </div>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
