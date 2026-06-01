import { Component } from '@angular/core';

@Component({
  selector: 'app-typing-indicator',
  standalone: true,
  template: `
    <div class="typing-wrap" role="status" aria-label="КАИ печатает...">
      <div class="avatar" aria-hidden="true">КАИ</div>
      <div class="bubble">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
      </div>
    </div>
  `,
  styles: [`
    .typing-wrap {
      display: flex;
      align-items: flex-end;
      gap: 10px;
      align-self: flex-start;
      animation: fadeIn 0.2s ease;
    }
    .avatar {
      width: 30px; height: 30px;
      border-radius: 50%;
      background: rgba(37, 99, 235, 0.18);
      color: #3b82f6;
      border: 1px solid rgba(37, 99, 235, 0.35);
      display: flex; align-items: center; justify-content: center;
      font-size: 10px; font-weight: 700; flex-shrink: 0;
    }
    .bubble {
      background: var(--color-bg-3);
      border: 1px solid var(--color-border);
      border-radius: 2px 12px 12px 12px;
      padding: 12px 16px;
      display: flex; align-items: center; gap: 5px;
    }
    .dot {
      width: 6px; height: 6px;
      border-radius: 50%;
      background: #3b82f6;
      animation: pulse 1.2s infinite;
      &:nth-child(2) { animation-delay: 0.2s; }
      &:nth-child(3) { animation-delay: 0.4s; }
    }
  `],
})
export class TypingIndicatorComponent {}
