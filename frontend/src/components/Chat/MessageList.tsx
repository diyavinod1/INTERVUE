import { useEffect, useRef } from "react";
import { MessageBubble } from "../MessageBubble/MessageBubble";
import { TypingIndicator } from "./TypingIndicator";
import type { ChatMessage } from "../../types/interview";

interface MessageListProps {
  conversation: ChatMessage[];
  isGenerating: boolean;
}

export function MessageList({ conversation, isGenerating }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [conversation.length, isGenerating]);

  return (
    <main className="min-h-0 flex-1 overflow-y-auto px-5 py-8 sm:px-6 sm:py-10">
      <div className="mx-auto flex max-w-3xl flex-col gap-9">
        {conversation.length === 0 && !isGenerating && (
          <p className="py-16 text-center text-sm text-ink-muted dark:text-paper/40">Your interview will begin here.</p>
        )}
        {conversation.map((message, i) => <MessageBubble key={`${message.created_at}-${i}`} message={message} />)}
        {isGenerating && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>
    </main>
  );
}
