# PUQ Chatbot: Copilot Style UI Redesign

## Overview
This design document captures the UI/UX overhaul for the React frontend, shifting from a "blocky dashboard" feel to a modern "Borderless Copilot UI" (AI-Native).

## Section 1: Chat Stream & Input
- **Message Stream**: Remove the heavy background colors, tight borders, and rigid bubble shapes for AI responses. User text can remain slightly highlighted, but AI responses should blend elegantly into the global background, leveraging typography and markdown structure over CSS boxes.
- **Chat Input Pill**: Redesign the bulky input box into a sleek, floating capsule (pill-shaped) docked at the bottom of the message view. Include frosted-glass effects (backdrop-blur) and soft shadows.

## Section 2: Summary Hub & Video List
- **Flat Sidebar**: Remove the card borders surrounding the Video List on the right. Transform it into a seamless right-side pane with a transparent frosted background.
- **Micro-animations**: Replace blocks of skeleton loaders with glowing ambient gradients and soft pulse effects.
- **Compact Actions**: Condense the "Video Details" block into a sticky, elegant top-label. Convert the large "Tóm tắt video" button into a subtle icon action button.

## Execution
Implementation will modify `ChatInput.tsx`, `MessageList.tsx`, and `ChatPage.tsx`.
