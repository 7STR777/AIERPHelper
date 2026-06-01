import { Component, output, input } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-message-input',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './message-input.component.html',
  styleUrls: ['./message-input.component.scss'],
})
export class MessageInputComponent {
  readonly disabled = input<boolean>(false);
  readonly sent = output<string>();

  text = '';

  send(): void {
    const trimmed = this.text.trim();
    if (!trimmed || this.disabled()) return;
    this.sent.emit(trimmed);
    this.text = '';
  }

  onKeydown(event: KeyboardEvent): void {
    // Enter без Shift — отправить
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.send();
    }
  }

  /** Вставить текст программно (из быстрых кнопок) */
  setAndSend(text: string): void {
    this.text = text;
    this.send();
  }
}
