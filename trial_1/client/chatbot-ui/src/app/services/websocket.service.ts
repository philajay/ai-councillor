import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';

@Injectable({
  providedIn: 'root'
})
export class WebsocketService {
  private socket$: WebSocketSubject<any>;
  private messagesSubject = new Subject<any>();
  public messages$ = this.messagesSubject.asObservable();

  constructor() {
    //https://ai-assistant-bot-183228620742.us-central1.run.app
    this.socket$ = webSocket('wss://ai-assistant-bot-183228620742.us-central1.run.app/bot');
    //this.socket$ = webSocket('ws://localhost:8080/bot');
    this.socket$.subscribe({
      next: (msg) => this.messagesSubject.next(msg),
      error: (err) => console.error(err),
      complete: () => console.warn('WebSocket connection closed')
    });
  }

  sendMessage(msg: any) {
    this.socket$.next(msg);
  }
}