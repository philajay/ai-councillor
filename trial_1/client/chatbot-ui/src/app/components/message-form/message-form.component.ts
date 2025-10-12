import { Component, EventEmitter, Output, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MessageService } from '../../services/message.service';
import { HttpService } from '../../services/http.service';
import { CommonModule } from '@angular/common';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-message-form',
  standalone: true,
  imports: [FormsModule, CommonModule, MatProgressSpinnerModule],
  templateUrl: './message-form.component.html',
  styleUrls: ['./message-form.component.css'],
})
export class MessageFormComponent implements OnInit {
  @Output() messageSent = new EventEmitter<void>();
  newMessage = '';
  showSpinner = false;

  constructor(
    private messageService: MessageService,
    private httpService: HttpService
  ) {}

  ngOnInit(): void {
    this.messageService.showSpinner$.subscribe(show => {
      this.showSpinner = show;
    });
  }

  sendMessage(): void {
    if (this.newMessage.trim()) {
      this.messageService.addMessage(this.newMessage, 'user', { clearChips: true });
      this.newMessage = '';
      this.messageSent.emit();
    }
  }
}