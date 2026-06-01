import {
  Component,
  inject,
  ViewChild,
  ElementRef,
  AfterViewChecked,
  effect,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatStateService } from '@core/services/chat-state.service';
import { MessageBubbleComponent } from '../message-bubble/message-bubble.component';
import { TypingIndicatorComponent } from '../typing-indicator/typing-indicator.component';
import { QuickActionsComponent } from '../quick-actions/quick-actions.component';
import { MessageInputComponent } from '../message-input/message-input.component';

@Component({
  selector: 'app-chat-window',
  standalone: true,
  imports: [
    CommonModule,
    MessageBubbleComponent,
    TypingIndicatorComponent,
    QuickActionsComponent,
    MessageInputComponent,
  ],
  templateUrl: './chat-window.component.html',
  styleUrls: ['./chat-window.component.scss'],
})
export class ChatWindowComponent implements AfterViewChecked {
  readonly chatState = inject(ChatStateService);

  @ViewChild('messagesContainer') private messagesContainer?: ElementRef<HTMLDivElement>;
  @ViewChild('messagesEnd') private messagesEnd?: ElementRef<HTMLDivElement>;

  private shouldScroll = false;

  constructor() {
    effect(() => {
      const _messages = this.chatState.messages();
      const _loading = this.chatState.isLoading();
      const _error = this.chatState.error();
      this.shouldScroll = true;
    });
  }

  ngAfterViewChecked(): void {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  onSend(text: string): void {
    this.chatState.sendMessage(text);
  }

  onQuickAction(text: string): void {
    this.chatState.sendMessage(text);
  }

  onRating(messageId: string, rating: 'good' | 'bad'): void {
    this.chatState.rateMessage(messageId, rating);
  }

  private scrollToBottom(): void {
    const container = this.messagesContainer?.nativeElement;
    if (!container) return;

    const distanceFromBottom =
      container.scrollHeight - container.scrollTop - container.clientHeight;

    // Не сбрасываем позицию, если пользователь читает старые сообщения
    if (distanceFromBottom > 120) return;

    container.scrollTop = container.scrollHeight;
  }
}
