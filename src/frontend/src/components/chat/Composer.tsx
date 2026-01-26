import { Paperclip, Send } from "lucide-react";
import { useRef } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

type ComposerProps = {
  input: string;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onUpload: (file: File) => void;
  loading: boolean;
  uploading: boolean;
};

export function Composer({
  input,
  onInputChange,
  onSend,
  onUpload,
  loading,
  uploading,
}: ComposerProps) {
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      onSend();
    }
  };

  return (
    <div className="border-t bg-background px-4 py-4">
      <div className="mx-auto flex max-w-4xl flex-col gap-3">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          Upload a deposition or ask a question. Shift+Enter for a new line.
        </div>
        <div className="flex items-end gap-2 rounded-2xl border bg-card px-3 py-2 shadow-sm">
          <Textarea
            className="min-h-[44px] resize-none border-0 bg-transparent p-2 text-sm shadow-none focus-visible:ring-0"
            onChange={(event) => onInputChange(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Send a message..."
            value={input}
          />
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".txt,.md,.pdf"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (!file) return;
              onUpload(file);
              event.target.value = "";
            }}
          />
          <Button
            className="h-9 w-9"
            disabled={uploading}
            onClick={() => fileInputRef.current?.click()}
            size="icon"
            variant="ghost"
          >
            <Paperclip className="size-4" />
          </Button>
          <Button
            className="h-9 w-9"
            disabled={loading || !input.trim()}
            onClick={onSend}
            size="icon"
          >
            <Send className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
