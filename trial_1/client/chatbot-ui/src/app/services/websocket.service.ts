import { Injectable, NgZone } from '@angular/core';
import { Subject } from 'rxjs';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import { ServerEvent } from '../models/server-event.model';

@Injectable({
  providedIn: 'root'
})
export class WebsocketService {
  private socket$!: WebSocketSubject<ServerEvent>;
  private messagesSubject = new Subject<ServerEvent>();
  public messages$ = this.messagesSubject.asObservable();
  private courseLevel: string | null = null;
  private host = "ws://localhost:8080"; // Make this configurable
  //private host = "wss://ai-assistant-bot-183228620742.us-central1.run.app"

  constructor(private zone: NgZone) {}

  private getSessionId(): string {
    let sessionId = localStorage.getItem('chatSessionId');
    if (!sessionId) {
      sessionId = crypto.randomUUID();
      localStorage.setItem('chatSessionId', sessionId);
    }
    return sessionId;
  }

  setCourseLevel(level: string) {
    this.courseLevel = level;
  }

  connect(message: string): void {
    this.disconnect();

    const sessionId = this.getSessionId();
    let url = `${this.host}/bot?sessionId=${sessionId}`;
    if (this.courseLevel) {
      url += `&courseLevel=${encodeURIComponent(this.courseLevel)}`;
    }

    this.socket$ = webSocket<ServerEvent>(url);
    this.socket$.subscribe({
      next: (msg) => this.zone.run(() => this.messagesSubject.next(msg)),
      error: (err) => {
        this.zone.run(() => {
          console.error('WebSocket failed:', err);
          this.messagesSubject.error({
            error: 'Connection Error',
            message: 'Could not connect to the server. Please try again later.'
          });
        });
      },
      complete: () => this.zone.run(() => console.warn('WebSocket connection closed'))
    });

    this.sendMessage({ text: message });
  }

  sendMessage(msg: { text: string }): void {
    if (this.socket$) {
      this.socket$.next(msg as ServerEvent);
    }
  }

  disconnect(): void {
    if (this.socket$) {
      this.socket$.complete();
      console.warn('WebSocket connection closed');
    }
  }
}
