import { Check, Copy, Send, Sparkles, ThumbsDown, ThumbsUp } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  spanId?: string;
  feedback?: "up" | "down";
};

type MessageBubbleProps = {
  message: ChatMessage;
  onFeedback: (rating?: "up" | "down", comment?: string) => void;
};

export function MessageBubble({ message, onFeedback }: MessageBubbleProps) {
  const isAssistant = message.role === "assistant";
  const [comment, setComment] = useState("");
  const [copied, setCopied] = useState(false);

  return (
    <div
      className="group/message fade-in w-full animate-in duration-200"
      data-role={message.role}
    >
      <div
        className={cn("flex w-full items-start gap-3", {
          "justify-end": !isAssistant,
          "justify-start": isAssistant,
        })}
      >
        {isAssistant && (
          <div className="-mt-1 flex size-8 shrink-0 items-center justify-center rounded-full bg-background ring-1 ring-border">
            <Sparkles className="size-4 text-foreground" />
          </div>
        )}

        <div
          className={cn("flex w-full flex-col gap-3", {
            "items-end": !isAssistant,
            "items-start": isAssistant,
          })}
        >
          <div
            className={cn(
              "rounded-2xl px-4 py-3 text-sm leading-relaxed",
              {
                "max-w-[min(640px,80%)] bg-primary text-primary-foreground":
                  !isAssistant,
                "w-full max-w-3xl bg-card text-foreground shadow-sm":
                  isAssistant,
              }
            )}
          >
            <div className="whitespace-pre-wrap">{message.content}</div>
          </div>

          {isAssistant && message.spanId && (
            <div className="flex w-full max-w-3xl items-center gap-2 text-muted-foreground">
              <Button
                className="h-8 w-8"
                onClick={async () => {
                  await navigator.clipboard.writeText(message.content);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 1500);
                }}
                size="icon"
                variant="ghost"
              >
                {copied ? (
                  <Check className="size-4" />
                ) : (
                  <Copy className="size-4" />
                )}
              </Button>
              <Button
                className="h-8 w-8"
                disabled={message.feedback === "up"}
                onClick={() => onFeedback("up", comment.trim() || undefined)}
                size="icon"
                variant="ghost"
              >
                <ThumbsUp className="size-4" />
              </Button>
              <Button
                className="h-8 w-8"
                disabled={message.feedback === "down"}
                onClick={() => onFeedback("down", comment.trim() || undefined)}
                size="icon"
                variant="ghost"
              >
                <ThumbsDown className="size-4" />
              </Button>
              <input
                className="h-9 flex-1 rounded-md border border-input bg-background px-3 text-sm text-foreground"
                onChange={(event) => setComment(event.target.value)}
                placeholder="Add a comment for feedback..."
                value={comment}
              />
              <Button
                className="h-9 w-9"
                disabled={!comment.trim()}
                onClick={() => {
                  onFeedback(message.feedback, comment.trim());
                  setComment("");
                }}
                size="icon"
                variant="outline"
              >
                <Send className="size-4" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
