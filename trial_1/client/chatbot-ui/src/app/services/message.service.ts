import { Injectable } from '@angular/core';
import { HttpService } from './http.service';
import { Subject, BehaviorSubject } from 'rxjs';
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
  isAction?:boolean;
  isIntermediateMessage?: boolean;
}

export interface Thread {
  id: string;
  name: string;
  messages: Message[];
  selectedCourse?: any;
}

@Injectable({
  providedIn: 'root'
})
export class MessageService {
  private readonly _message = `I'm here to help you navigate the exciting world of our university's courses and programs. My goal is to provide you with quick, accurate, and easily accessible information, acting as your personal guide to academic offerings and administrative processes.
<br>
1.  I have done my 12th in arts with 60%. What courses am I eligible for?<br>
2.  Tell me about the Bachelor of Science in Computer Science program?<br>
3.  Or Just say Hi`;

  private threads = new Map<string, Thread>();
  private activeThreadId: string = 'explore';

  messagesUpdated = new Subject<string>();
  private isNewMessageStream = true;

  private courseInfoSubject = new BehaviorSubject<any[] | null>(null);
  public courseInfo$ = this.courseInfoSubject.asObservable();

  private showSpinnerSubject = new BehaviorSubject<boolean>(false);
  public showSpinner$ = this.showSpinnerSubject.asObservable();

  constructor(
    private httpService: HttpService
    ) {
    this.threads.set('explore', {
      id: 'explore',
      name: 'Chat',
      messages: [{ text: this._message, sender: 'bot' }],
    });
    this.httpService.messages$.subscribe({
      next: (event) => this.handleServerEvent(event),
      error: (err) => this.handleServerEvent(err)
    });
  }

  get activeThread(): Thread {
    return this.threads.get(this.activeThreadId)!;
  }

  get messages(): Message[] {
    return this.activeThread.messages;
  }

  getThreads(): Thread[] {
    return Array.from(this.threads.values());
  }

  setActiveThread(threadId: string): void {
    if (this.threads.has(threadId)) {
      this.activeThreadId = threadId;
      this.messagesUpdated.next(threadId);
    }
  }

  createCourseThread(course: any): string {
    const threadId = `course_${course.id}`;
    if (!this.threads.has(threadId)) {
      const initialMessage: Message = {
        text: '',
        sender: 'bot',
        isComponent: true,
        component: 'course-details',
        componentData: course,
      };
      this.threads.set(threadId, {
        id: threadId,
        name: course.name,
        messages: [initialMessage],
        selectedCourse: course,
      });
    }
    this.setActiveThread(threadId);
    return threadId;
  }

  addMessage(text: string, sender: 'user' | 'bot', options: { clearChips?: boolean } = {}) {
    this.activeThread.messages.push({ text, sender });
    if (sender === 'user') {
      this.isNewMessageStream = true;
      if (this.activeThread.selectedCourse) {
        this.httpService.sendCourseMessage({ text, courseId: this.activeThread.selectedCourse.id.toString() });
      } else {
        this.httpService.sendMessage({ text });
      }
    }
    this.messagesUpdated.next(this.activeThreadId);
  }

  private removeLoadingMessage() {
    const loadingMessageIndex = this.messages.findIndex(m => m.isLoading);
    if (loadingMessageIndex !== -1) {
      this.messages.splice(loadingMessageIndex, 1);
    }
  }

  private handleServerEvent(event: ServerEvent | { error: string; message: string }) {
    if ('progress_spinner' in event) {
      this.showSpinnerSubject.next(event.progress_spinner === 'start');
      return;
    }

    const isMeaningfulEvent = 'error' in event || event.endOfTurn ;

    if (isMeaningfulEvent && (event as any).agent && (event as any).agent == "auto_agent") {
      this.removeLoadingMessage();
    }

    if ('error' in event) {
      this.handleErrorEvent(event);
    } else if (event.action === 'functionCall') {
      this.handleFunctionCall(event);
    } else if (event.isIntermediateMessage) {
      this.handleTextMessage(event);
    } else if (event.endOfTurn) {
      this.handleEndOfTurn(event.agent || '');
    } else if (event.text) {
      this.handleTextMessage(event);
    }
   }

  private handleErrorEvent(event: { error: string; message: string }) {
    this.removeLoadingMessage();
    const lastUserMessage = [...this.messages].reverse().find(m => m.sender === 'user');
    if (lastUserMessage) {
      this.messages.push({
        text: `Sorry, an error occurred: ${event.message}. Please try again.`,
        sender: 'bot',
        isError: true,
        retryable: true,
        originalText: lastUserMessage.text,
      });
      this.messagesUpdated.next(this.activeThreadId);
    }
  }

  private handleFunctionCall(event: ServerEvent) {
    if (event.name === 'find_by_eligibility') {
      this.messages.push({
        text: '',
        sender: 'bot',
        isComponent: true,
        component: 'course-chips',
        componentData: event.results as string[]
      });
      this.messagesUpdated.next(this.activeThreadId);
    }

    if (event.name === 'find_by_discovery') {
      let componentData =  event.results || [];
      //remove the first element in array
      componentData = componentData.slice(1);
      //component data is array of arrays where we are interested in element at index 1. So we flatten it.
      componentData = componentData.flatMap((item: any) => {
        item[1].id = item[0]; //set id of course as first element
        item[1].stream = item[3]; //set stream of course as second element
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
        componentData: componentData
      });
      this.messagesUpdated.next(this.activeThreadId);
    }
  }

  private handleEndOfTurn(agent:string) {
    this.activeThread.messages = this.messages.filter(m => !m.isIntermediateMessage);
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

  private handleTextMessage(event: ServerEvent) {
    const text = event.text ?? '';
    if (this.isNewMessageStream) {
      this.messages.push({ text, sender: 'bot', isIntermediateMessage: event.isIntermediateMessage });
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
    this.messagesUpdated.next(this.activeThreadId);
  }

  private addBotMessage(lastMessage:any) {
    let agentName = lastMessage.agent;
    let jsonData = lastMessage.json;
    const message: Message = {
      sender: 'bot',
      isJson: true,
      text: ''
    };

    if(agentName === 'extract_order_entity' || agentName === 'auto_agent' || agentName == "course_sales_agent"){
      console.log(JSON.stringify(jsonData,  null, 2))
    }

    if (agentName === 'extract_order_entity' && jsonData.clarification_question) {
      console.log(`Clarification question found ${JSON.stringify(jsonData)}`);
      message.text = jsonData.clarification_question;
    } else if (jsonData.agentId) {
      message.text = jsonData.purpose;
    }  else if(lastMessage.agent === "auto_agent" || agentName == "course_sales_agent"){
        message.isJson = false;
        message.text = jsonData["markdown"]
    } else {
      //message.text = "Processing request. Hang tight.."
      return
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