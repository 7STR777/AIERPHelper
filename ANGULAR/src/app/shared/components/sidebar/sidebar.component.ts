import { Component, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { ChatStateService } from '@core/services/chat-state.service';
import { ChatSession } from '@core/models/chat.models';

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [CommonModule, RouterLink, RouterLinkActive],
  templateUrl: './sidebar.component.html',
  styleUrls: ['./sidebar.component.scss'],
})
export class SidebarComponent {
  private readonly chatState = inject(ChatStateService);

  readonly sessions = this.chatState.sessions;
  readonly activeSessionId = this.chatState.activeSessionId;

  newChat(): void {
    this.chatState.createSession();
  }

  selectSession(id: string): void {
    this.chatState.selectSession(id);
  }

  deleteSession(event: Event, id: string): void {
    event.stopPropagation();
    this.chatState.deleteSession(id);
  }

  formatDate(date: Date): string {
    return new Intl.DateTimeFormat('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  }
}
