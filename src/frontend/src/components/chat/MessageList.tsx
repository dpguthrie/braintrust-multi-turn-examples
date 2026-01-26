import { ArrowDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Greeting } from "./Greeting";
import { MessageBubble } from "./MessageBubble";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  spanId?: string;
  feedback?: "up" | "down";
};

type MessageListProps = {
  messages: ChatMessage[];
  loading: boolean;
  onFeedback: (index: number, rating?: "up" | "down", comment?: string) => void;
};

export function MessageList({ messages, loading, onFeedback }: MessageListProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [isAtBottom, setIsAtBottom] = useState(true);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, loading]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const handleScroll = () => {
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
      setIsAtBottom(atBottom);
    };
    el.addEventListener("scroll", handleScroll);
    return () => el.removeEventListener("scroll", handleScroll);
  }, []);

  const scrollToBottom = () => {
    const el = containerRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  };

  return (
    <div className="relative flex-1">
      <div className="h-full overflow-y-auto" ref={containerRef}>
        <div className="mx-auto flex w-full max-w-4xl flex-col gap-4 px-4 py-6">
          {messages.length === 0 && <Greeting />}
          {messages.map((message, index) => (
            <MessageBubble
              key={`${message.role}-${index}`}
              message={message}
              onFeedback={(rating, comment) =>
                onFeedback(index, rating, comment)
              }
            />
          ))}
          {loading && (
            <div className="text-sm text-muted-foreground">Thinking...</div>
          )}
        </div>
      </div>
      <Button
        className={`absolute bottom-4 left-1/2 h-9 w-9 -translate-x-1/2 rounded-full shadow ${
          isAtBottom ? "scale-0 opacity-0" : "scale-100 opacity-100"
        }`}
        onClick={scrollToBottom}
        size="icon"
        variant="outline"
      >
        <ArrowDown className="size-4" />
      </Button>
    </div>
  );
}
