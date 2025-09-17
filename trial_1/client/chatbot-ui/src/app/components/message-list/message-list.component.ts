import { Component, OnInit } from '@angular/core';
import { Message, MessageService } from '../../services/message.service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-message-list',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './message-list.component.html',
  styleUrls: ['./message-list.component.css']
})
export class MessageListComponent implements OnInit {
  messages: Message[] = [];

  constructor(private messageService: MessageService) { }

  ngOnInit(): void {
    this.messages = this.messageService.messages;
  }
}