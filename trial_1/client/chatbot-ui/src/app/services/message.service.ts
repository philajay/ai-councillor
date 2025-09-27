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
  agent?: any;
  isError?: boolean;
  retryable?: boolean;
  originalText?: string;
  isLoading?: boolean;
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
    if (sender === 'user') {
      this.isNewMessageStream = true;
      this.messages.push({ text: '', sender: 'bot', isLoading: true });
    }
    this.messagesUpdated.next();
  }

  private removeLoadingMessage() {
    const loadingMessageIndex = this.messages.findIndex(m => m.isLoading);
    if (loadingMessageIndex !== -1) {
      this.messages.splice(loadingMessageIndex, 1);
    }
  }

  private handleServerEvent(event: ServerEvent | { error: string; message: string }) {
    const isMeaningfulEvent = 'error' in event || event.action || event.endOfTurn || event.text;

    if (isMeaningfulEvent) {
      this.removeLoadingMessage();
    }

    if ('error' in event) {
      this.handleErrorEvent(event);
    } else if (event.action === 'functionCall') {
      this.handleFunctionCall(event);
    } else if (event.endOfTurn) {
      this.handleEndOfTurn(event.agent || '');
    } else if (event.text) {
      this.handleTextMessage(event.text);
    }
  }

  private handleErrorEvent(event: { error: string; message: string }) {
    const lastUserMessage = [...this.messages].reverse().find(m => m.sender === 'user');
    if (lastUserMessage) {
      this.messages.push({
        text: `Sorry, an error occurred: ${event.message}. Please try again.`,
        sender: 'bot',
        isError: true,
        retryable: true,
        originalText: lastUserMessage.text,
      });
      this.messagesUpdated.next();
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
        componentData: event.results || [],
      });
      this.messagesUpdated.next();
    }

    if (event.name === 'find_by_discovery') {
      let componentData =  event.results || [];
      //remove the first element in array
      componentData = componentData.slice(1);
      //component data is array of arrays where we are interested in element at index 1. So we flatten it.
      componentData = componentData.flatMap((item: any) => {
        item[1].id = item[0]; //set id of course as first element
        return item[1];
      });

      //Strip the summary if more than 200 characters and add "..." at the end
      componentData = componentData.map((item: any) => {
        if (item.summary && item.summary.length > 200) {
          item.summary = item.summary.substring(0, 200) + '...';
        }
        return item;
      });
      

      this.messages.push({
        text: '',
        sender: 'bot',
        isComponent: true,
        component: 'course-info',
        componentData: componentData,
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
      console.log(`Clarification question found ${jsonData}`);
      message.text = jsonData.clarification_question;
    } else if (jsonData.agentId) {
      message.text = jsonData.purpose;
    }  else if(lastMessage.agent === "summazier"){
      message.text = JSON.stringify(jsonData, null, 2);
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