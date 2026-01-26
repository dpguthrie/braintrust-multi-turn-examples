import { PlusIcon } from "lucide-react";

import { Button } from "@/components/ui/button";
import { SidebarTrigger } from "@/components/ui/sidebar";

type ChatHeaderProps = {
  conversationId: string;
  onNewChat: () => void;
};

export function ChatHeader({ conversationId, onNewChat }: ChatHeaderProps) {
  return (
    <header className="sticky top-0 z-10 flex items-center gap-2 border-b bg-background px-4 py-3">
      <SidebarTrigger />
      <div className="flex flex-col">
        <span className="text-sm font-semibold">Rev LangGraph Demo</span>
        <span className="text-xs text-muted-foreground">
          Conversation: {conversationId}
        </span>
      </div>
      <Button
        className="ml-auto h-8 gap-1"
        onClick={onNewChat}
        variant="outline"
      >
        <PlusIcon className="size-4" />
        New chat
      </Button>
    </header>
  );
}
