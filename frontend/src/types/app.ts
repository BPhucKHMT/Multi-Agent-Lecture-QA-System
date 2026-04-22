export type AppSection = "chatspace" | "summaryhub";

export type DiscussionContext = {
  title: string;
  subtitle: string;
  summaryText?: string; // Nội dung tóm tắt để inject vào Chatspace
};
