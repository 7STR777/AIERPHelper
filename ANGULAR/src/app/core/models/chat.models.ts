export type MessageRole = 'user' | 'bot';
export type MessageStatus = 'sending' | 'sent' | 'error';
export type MessageRating = 'good' | 'bad' | null;

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  status?: MessageStatus;
  rating?: MessageRating;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: Date;
  updatedAt: Date;
  messages: Message[];
}
