import { Injectable } from '@angular/core';
import { WebsocketService } from './websocket.service';

export interface Message {
  text: string;
  sender: 'user' | 'bot';
}

@Injectable({
  providedIn: 'root'
})
export class MessageService {
  messages: Message[] = [
    { text: 'Hello! How can I help you today?', sender: 'bot' }
  ];
  private isNewMessageStream = true;

  constructor(private websocketService: WebsocketService) {
    this.websocketService.messages$.subscribe(event => {
      this.handleServerEvent(event);
    });
  }

  addMessage(text: string, sender: 'user' | 'bot') {
    this.messages.push({ text, sender });
    if (sender === 'user') {
      this.isNewMessageStream = true;
    }
  }

  private handleServerEvent(event: any) {
    if (event.endOfTurn) {
      this.isNewMessageStream = true;
      return;
    }

    if (event.text) {
      if (this.isNewMessageStream) {
        this.messages.push({ text: event.text, sender: 'bot' });
        this.isNewMessageStream = false;
      } else {
        const lastMessage = this.messages[this.messages.length - 1];
        if (lastMessage && lastMessage.sender === 'bot') {
          lastMessage.text += event.text;
        }
      }
    }
  }
}