import { Component, EventEmitter, Output } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MessageService } from '../../services/message.service';
import { WebsocketService } from '../../services/websocket.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-message-form',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './message-form.component.html',
  styleUrls: ['./message-form.component.css']
})
export class MessageFormComponent {
  @Output() messageSent = new EventEmitter<void>();
  newMessage: string = '';

  constructor(
    private messageService: MessageService,
    private websocketService: WebsocketService
  ) { }

  sendMessage() {
    if (this.newMessage.trim()) {
      this.messageService.addMessage(this.newMessage, 'user', { clearChips: true });
      this.websocketService.sendMessage({ text: this.newMessage });
      this.newMessage = '';
      this.messageSent.emit();
    }
  }
}