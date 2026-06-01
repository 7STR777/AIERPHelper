import { Injectable, inject, signal, computed, effect } from '@angular/core';
import { ChatApiService } from './chat-api.service';
import { AuthService } from './auth.service';
import { Message, ChatSession } from '../models/chat.models';

const STORAGE_PREFIX = 'gst_kai_chats_v1_';
const DEFAULT_TITLE = 'Новый диалог';

interface StoredChatData {
  sessions: ChatSession[];
  activeSessionId: string | null;
}

@Injectable({ providedIn: 'root' })
export class ChatStateService {
  private readonly api = inject(ChatApiService);
  private readonly auth = inject(AuthService);

  private currentUserLogin: string | null = null;
  private skipNextSave = false;

  readonly sessions        = signal<ChatSession[]>([]);
  readonly activeSessionId = signal<string | null>(null);
  readonly isLoading       = signal(false);
  readonly error           = signal<string | null>(null);

  readonly activeSession = computed(() =>
    this.sessions().find(s => s.id === this.activeSessionId()) ?? null
  );
  readonly messages = computed(() => this.activeSession()?.messages ?? []);

  constructor() {
    effect(() => {
      const login = this.auth.user()?.login ?? null;
      if (login === this.currentUserLogin) return;

      if (this.currentUserLogin) {
        this.saveToStorage(this.currentUserLogin);
      }

      this.currentUserLogin = login;

      if (login) {
        this.loadFromStorage(login);
      } else {
        this.clearState();
      }
    }, { allowSignalWrites: true });

    effect(() => {
      const login = this.currentUserLogin;
      if (!login || this.skipNextSave) return;

      const data: StoredChatData = {
        sessions: this.sessions(),
        activeSessionId: this.activeSessionId(),
      };
      this.saveToStorage(login, data);
    });
  }

  createSession(): void {
    const id = crypto.randomUUID();
    this.sessions.update(s => [{
      id,
      title: DEFAULT_TITLE,
      createdAt: new Date(),
      updatedAt: new Date(),
      messages: [],
    }, ...s]);
    this.activeSessionId.set(id);
    this.error.set(null);
  }

  selectSession(id: string): void {
    this.activeSessionId.set(id);
    this.error.set(null);
  }

  deleteSession(id: string): void {
    this.sessions.update(s => s.filter(x => x.id !== id));
    if (this.activeSessionId() === id) {
      this.activeSessionId.set(this.sessions()[0]?.id ?? null);
    }
  }

  sendMessage(text: string): void {
    if (!text.trim() || this.isLoading()) return;
    if (!this.activeSessionId()) this.createSession();

    const sessionId = this.activeSessionId()!;
    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text.trim(),
      timestamp: new Date(),
      status: 'sending',
    };

    this.addMessage(sessionId, userMsg);
    this.setTitleFromFirstMessage(sessionId, text.trim());
    this.isLoading.set(true);
    this.error.set(null);

    this.api.ask(text.trim()).subscribe({
      next: (res) => {
        this.updateMessageStatus(sessionId, userMsg.id, 'sent');
        this.addMessage(sessionId, {
          id: res.messageID,
          role: 'bot',
          content: res.content,
          timestamp: new Date(res.timestamp),
          rating: null,
        });
        this.isLoading.set(false);
      },
      error: (err: Error) => {
        this.updateMessageStatus(sessionId, userMsg.id, 'error');
        this.error.set(err.message ?? 'Не удалось получить ответ. Проверьте соединение.');
        this.isLoading.set(false);
      },
    });
  }

  rateMessage(messageId: string, rating: 'good' | 'bad'): void {
    const session = this.activeSession();
    if (!session) return;

    const msg = session.messages.find(m => m.id === messageId);
    if (!msg || msg.role !== 'bot') return;

    const idx = session.messages.indexOf(msg);
    const question = idx > 0 ? session.messages[idx - 1].content : '';

    this.sessions.update(sessions => sessions.map(s => {
      if (s.id !== session.id) return s;
      return {
        ...s,
        messages: s.messages.map(m => (m.id === messageId ? { ...m, rating } : m)),
      };
    }));

    this.api.submitRating({ question, answer: msg.content, rating }).subscribe();
  }

  private clearState(): void {
    this.skipNextSave = true;
    this.sessions.set([]);
    this.activeSessionId.set(null);
    this.error.set(null);
    this.isLoading.set(false);
    this.skipNextSave = false;
  }

  private loadFromStorage(login: string): void {
    this.skipNextSave = true;

    try {
      const raw = localStorage.getItem(STORAGE_PREFIX + login);
      if (!raw) {
        this.sessions.set([]);
        this.activeSessionId.set(null);
      } else {
        const data = this.deserialize(raw);
        this.sessions.set(data.sessions);
        const activeId = data.activeSessionId;
        this.activeSessionId.set(
          activeId && data.sessions.some(s => s.id === activeId)
            ? activeId
            : data.sessions[0]?.id ?? null
        );
      }
    } catch {
      this.sessions.set([]);
      this.activeSessionId.set(null);
    }

    this.error.set(null);
    this.skipNextSave = false;
  }

  private saveToStorage(login: string, data?: StoredChatData): void {
    const payload = data ?? {
      sessions: this.sessions(),
      activeSessionId: this.activeSessionId(),
    };

    try {
      localStorage.setItem(STORAGE_PREFIX + login, JSON.stringify(payload));
    } catch {
      // localStorage переполнен — история остаётся только в памяти
    }
  }

  private deserialize(raw: string): StoredChatData {
    const parsed = JSON.parse(raw) as StoredChatData;

    return {
      activeSessionId: parsed.activeSessionId ?? null,
      sessions: (parsed.sessions ?? []).map(s => ({
        ...s,
        createdAt: new Date(s.createdAt),
        updatedAt: new Date(s.updatedAt),
        messages: (s.messages ?? []).map(m => ({
          ...m,
          timestamp: new Date(m.timestamp),
        })),
      })),
    };
  }

  private addMessage(sessionId: string, message: Message): void {
    this.sessions.update(sessions => sessions.map(s => {
      if (s.id !== sessionId) return s;
      return { ...s, messages: [...s.messages, message], updatedAt: new Date() };
    }));
  }

  private updateMessageStatus(sessionId: string, msgId: string, status: Message['status']): void {
    this.sessions.update(sessions => sessions.map(s => {
      if (s.id !== sessionId) return s;
      return {
        ...s,
        messages: s.messages.map(m => (m.id === msgId ? { ...m, status } : m)),
        updatedAt: new Date(),
      };
    }));
  }

  /** Название диалога = первый запрос пользователя (обрезается до 50 символов). */
  private setTitleFromFirstMessage(sessionId: string, text: string): void {
    const title = this.formatDialogTitle(text);

    this.sessions.update(sessions => sessions.map(s => {
      if (s.id !== sessionId) return s;

      const userMessageCount = s.messages.filter(m => m.role === 'user').length;
      if (userMessageCount !== 1) return s;

      return { ...s, title };
    }));
  }

  private formatDialogTitle(text: string): string {
    const normalized = text.trim().replace(/\s+/g, ' ');
    if (!normalized) return DEFAULT_TITLE;
    return normalized.length > 50 ? `${normalized.slice(0, 50)}…` : normalized;
  }
}
