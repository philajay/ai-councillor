import { Injectable } from '@angular/core';
import { WebsocketService } from './websocket.service';
import { Subject } from 'rxjs';
import { ServerEvent } from '../models/server-event.model';

export interface Message {
  text: string;
  sender: 'user' | 'bot';
  isJson?: boolean;
  json?: any;
  isComponent?: boolean;
  component?: string;
  componentData?: any;
  agent?:any;
}

@Injectable({
  providedIn: 'root'
})
export class MessageService {
  private readonly _message = `I'm here to help you navigate the exciting world of our university's courses and programs. My goal is to provide you with quick, accurate, and easily accessible information, acting as your personal guide to academic offerings and administrative processes.
<br>
1.  I have done my 12th in arts with 60%. What courses am I eligible for?<br>
2.  Tell me about the Bachelor of Science in Computer Science program?<br>
3.  Tell me about placements in BCA Program.`;

  messages: Message[] = [{ text: this._message, sender: 'bot' }];
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

  private handleServerEvent(event: ServerEvent) {
    if (event.action === 'functionCall') {
      this.handleFunctionCall(event);
    } else if (event.endOfTurn) {
      this.handleEndOfTurn(event.agent || '');
    } else if (event.text) {
      this.handleTextMessage(event.text);
    }
  }

  private handleFunctionCall(event: ServerEvent) {
    if (event.name === 'find_by_eligibility') {
      this.messages.push({
        text: 'Please select one of the following courses:',
        sender: 'bot'
      });
      this.messages.push({
        text: '',
        sender: 'bot',
        isComponent: true,
        component: 'course-chips',
        componentData: event.results
      });
      this.messagesUpdated.next();
    }
  }

  private handleEndOfTurn(agent:string) {
    this.isNewMessageStream = true;
    const lastMessage = this.messages[this.messages.length - 1];
    if (lastMessage?.sender === 'bot') {
      lastMessage.agent = agent
      try {
        const cleanedJson = this.cleanJsonString(lastMessage.text);
        lastMessage.json = JSON.parse(cleanedJson);
        lastMessage.isJson = true;
        this.messages.pop();
        this.addBotMessage(lastMessage);
      } catch (e) {
        lastMessage.isJson = false;
      }
    }
  }

  private handleTextMessage(text: string) {
    if (this.isNewMessageStream) {
      this.messages.push({ text, sender: 'bot' });
      this.isNewMessageStream = false;
    } else {
      const lastMessage = this.messages[this.messages.length - 1];
      if (lastMessage?.sender === 'bot') {
        lastMessage.text += text;
        try {
          const cleanedJson = this.cleanJsonString(lastMessage.text);
          lastMessage.json = JSON.parse(cleanedJson);
          lastMessage.isJson = true;
        } catch (e) {
          lastMessage.isJson = false;
        }
      }
    }
    this.messagesUpdated.next();
  }

  private addBotMessage(lastMessage:any) {
    let jsonData = lastMessage.json;
    const message: Message = {
      sender: 'bot',
      isJson: true,
      text: ''
    };

    if (lastMessage.agent == 'json_formatter') {
      this.messages.push({
        text: '',
        sender: 'bot',
        isComponent: true,
        component: 'course-info',
        componentData: jsonData,
      });
      this.messagesUpdated.next();
      return;
    } else if (jsonData.agentId === 2 && jsonData.clarification_question) {
      message.text = jsonData.clarification_question;
    } else if (jsonData.agentId) {
      message.text = jsonData.purpose;
    }

    if(jsonData.agentId == "get_eligibility"){
      return
    }

    

    this.messages.push(message);
  }

  private cleanJsonString(jsonString: string): string {
    return jsonString.replace(/```json\n|```/g, '').trim();
  }
}