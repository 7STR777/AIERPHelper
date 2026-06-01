import { Component, output } from '@angular/core';

const QUICK_QUESTIONS = [
  'Как создать производственный заказ?',
  'Где найти складской учёт?',
  'Как закрыть финансовый период?',
  'Как сформировать отчёт?',
  'Управление правами доступа',
  'Как провести инвентаризацию?',
];

@Component({
  selector: 'app-quick-actions',
  standalone: true,
  template: `
    <div class="quick-wrap" role="list" aria-label="Частые вопросы">
      @for (q of questions; track q) {
        <button class="quick-btn" (click)="select(q)" role="listitem">{{ q }}</button>
      }
    </div>
  `,
  styles: [`
    .quick-wrap {
      display: flex;
      flex-wrap: wrap;
      gap: 7px;
      padding: 0 20px 12px;
    }
    .quick-btn {
      padding: 5px 13px;
      border: 1px solid var(--color-border-2);
      border-radius: 20px;
      background: none;
      color: var(--color-text-2);
      font-size: 12px;
      font-family: var(--font-main);
      cursor: pointer;
      transition: all 0.18s;
      white-space: nowrap;

      &:hover {
        border-color: var(--color-accent-2);
        color: var(--color-accent-2);
        background: var(--color-accent-3);
      }
    }
  `],
})
export class QuickActionsComponent {
  readonly questions = QUICK_QUESTIONS;
  readonly selected = output<string>();

  select(q: string): void {
    this.selected.emit(q);
  }
}
