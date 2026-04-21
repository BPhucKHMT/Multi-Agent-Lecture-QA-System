import React, { type ReactNode } from "react";
import { BrowserRouter } from "react-router-dom";
import { ConversationStoreProvider } from "../store/conversationStore";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <BrowserRouter>
      <ConversationStoreProvider>
        {children}
      </ConversationStoreProvider>
    </BrowserRouter>
  );
}
