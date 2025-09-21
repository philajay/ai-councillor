import { Injectable } from '@angular/core';
import { WebsocketService } from './websocket.service';
import { Subject } from 'rxjs';

export interface Message {
  text: string;
  sender: 'user' | 'bot';
  isJson?: boolean;
  json?:any;
}

@Injectable({
  providedIn: 'root'
})
export class MessageService {
  messages: Message[] = [
    { text: 'Hello! How can I help you today?', sender: 'bot' }
  ];
  messagesUpdated = new Subject<void>();
  private isNewMessageStream = true;

  constructor(private websocketService: WebsocketService) {
    this.websocketService.messages$.subscribe(event => {
      this.handleServerEvent(event);
    });
  }

  addMessage(text: string, sender: 'user' | 'bot') {
    this.messages.push({ text, sender });
    this.messagesUpdated.next();
    if (sender === 'user') {
      this.isNewMessageStream = true;
    }
  }

  private handleServerEvent(event: any) {
    if (event.endOfTurn) {
      this.isNewMessageStream = true;
      const lastMessage = this.messages[this.messages.length - 1];
        if (lastMessage && lastMessage.sender === 'bot' ) {
          try{
            const cleanedJson = this.cleanJsonString(lastMessage.text);
            lastMessage.json = JSON.parse(cleanedJson);
            lastMessage.isJson = true;
            this.messages.pop();
            this.addMessageBasedOnAgent(lastMessage.json)
          }catch(e){
            lastMessage.isJson = false;
          }
          finally {

          }
        }
      return;
    }

    if (event.text) {
      if (this.isNewMessageStream) {
        this.messages.push({ text: event.text, sender: 'bot' });
        this.isNewMessageStream = false;
      } else {
        const lastMessage = this.messages[this.messages.length - 1];
        if (lastMessage && lastMessage.sender === 'bot' && event.text) {
          lastMessage.text += event.text;
          try{
            const cleanedJson = this.cleanJsonString(lastMessage.text);
            lastMessage.json = JSON.parse(cleanedJson);
            lastMessage.isJson = true;
          }catch(e){
            lastMessage.isJson = false;
          }
        }
      }
      this.messagesUpdated.next();
    }
  }

  private addMessageBasedOnAgent(jsonData:any){
    let message = {
      sender: "bot",
      isJson: true,
      text: ''
    } as Message
    if (jsonData.agentId == 2 && jsonData.clarification_question){
      //this.addMessage(jsonData.clarification_question, "bot");
      message.text  = jsonData.clarification_question
    }
    else if(jsonData.agentId){
      message.text  = jsonData.purpose
    }

    this.messages.push(message)
  }

  private cleanJsonString(jsonString: string): string {
    return jsonString.replace(/```json\n|```/g, '').trim();
  }
}