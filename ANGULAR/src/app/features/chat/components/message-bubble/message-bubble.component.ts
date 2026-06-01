import { Component, input, output } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { Message } from '@core/models/chat.models';

@Component({
  selector: 'app-message-bubble',
  standalone: true,
  imports: [CommonModule, DatePipe],
  templateUrl: './message-bubble.component.html',
  styleUrls: ['./message-bubble.component.scss'],
})
export class MessageBubbleComponent {
  message = input.required<Message>();
  rated = output<'good' | 'bad'>();

  rate(value: 'good' | 'bad'): void {
    this.rated.emit(value);
  }
}
