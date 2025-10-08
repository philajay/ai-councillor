import { Component, EventEmitter, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MessageService } from '../../services/message.service';
import { HttpService } from '../../services/http.service';

@Component({
  selector: 'app-message-form',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './message-form.component.html',
  styleUrls: ['./message-form.component.css'],
})
export class MessageFormComponent {
  @Output() messageSent = new EventEmitter<void>();
  newMessage = '';

  constructor(
    private messageService: MessageService,
    private httpService: HttpService
  ) {}

  sendMessage(): void {
    if (this.newMessage.trim()) {
      this.messageService.addMessage(this.newMessage, 'user', { clearChips: true });
      this.httpService.sendMessage({ text: this.newMessage });
      this.newMessage = '';
      this.messageSent.emit();
    }
  }
}