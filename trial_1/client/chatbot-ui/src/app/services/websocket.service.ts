import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { ServerEvent } from '../models/server-event.model';

@Injectable({
  providedIn: 'root'
})
export class WebsocketService {
  private socket$: WebSocketSubject<ServerEvent>;
  private messagesSubject = new Subject<ServerEvent>();
  public messages$ = this.messagesSubject.asObservable();

  constructor() {
    //https://ai-assistant-bot-183228620742.us-central1.run.app
    //this.socket$ = webSocket('wss://ai-assistant-bot-183228620742.us-central1.run.app/bot');
    this.socket$ = webSocket<ServerEvent>('ws://localhost:8080/bot');
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