import { useState } from "react";

import { sendChat, sendFeedback, uploadDocument } from "./api";
import { ChatHeader } from "@/components/chat/ChatHeader";
import { Composer } from "@/components/chat/Composer";
import { MessageList } from "@/components/chat/MessageList";
import { AppSidebar } from "@/components/sidebar/AppSidebar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  spanId?: string;
  feedback?: "up" | "down";
};

function initializeConversationId(): string {
  const key = "conversation_id";
  const existing = localStorage.getItem(key);
  if (existing) return existing;
  const id = crypto.randomUUID();
  localStorage.setItem(key, id);
  return id;
}

export default function App() {
  const [conversationId, setConversationId] = useState(() =>
    initializeConversationId()
  );
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  const handleNewChat = () => {
    const id = crypto.randomUUID();
    localStorage.setItem("conversation_id", id);
    setConversationId(id);
    setMessages([]);
    setInput("");
  };

  const handleSend = async () => {
    if (!input.trim()) return;
    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);
    try {
      const response = await sendChat(conversationId, userMessage);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.assistant_message,
          spanId: response.span_id,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Error: unable to reach the agent." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (
    index: number,
    rating?: "up" | "down",
    comment?: string
  ) => {
    const message = messages[index];
    if (!message.spanId) return;
    await sendFeedback(message.spanId, rating, comment);
    if (rating) {
      setMessages((prev) =>
        prev.map((item, i) =>
          i === index ? { ...item, feedback: rating } : item
        )
      );
    }
  };

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      await uploadDocument(conversationId, file);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Document uploaded: ${file.name}`,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Upload failed. Please try again." },
      ]);
    } finally {
      setUploading(false);
    }
  };

  return (
    <SidebarProvider defaultOpen>
      <AppSidebar onNewChat={handleNewChat} />
      <SidebarInset className="flex h-svh flex-col">
        <ChatHeader
          conversationId={conversationId}
          onNewChat={handleNewChat}
        />
        <MessageList
          loading={loading}
          messages={messages}
          onFeedback={handleFeedback}
        />
        <Composer
          input={input}
          loading={loading}
          onInputChange={setInput}
          onSend={handleSend}
          onUpload={handleUpload}
          uploading={uploading}
        />
      </SidebarInset>
    </SidebarProvider>
  );
}
