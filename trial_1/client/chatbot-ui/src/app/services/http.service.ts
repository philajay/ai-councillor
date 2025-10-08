import { Injectable, NgZone } from '@angular/core';
import { Subject } from 'rxjs';
import { ServerEvent } from '../models/server-event.model';

@Injectable({
  providedIn: 'root'
})
export class HttpService {
  private eventSource: EventSource | null = null;
  private messagesSubject = new Subject<ServerEvent>();
  public messages$ = this.messagesSubject.asObservable();
  private courseLevel: string | null = null;

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
    // Disconnect any existing connection
    this.disconnect();

    const sessionId = this.getSessionId();
    let url = `http://localhost:8080/chat?text=${encodeURIComponent(message)}&sessionId=${sessionId}`;
    if (this.courseLevel) {
      url += `&courseLevel=${encodeURIComponent(this.courseLevel)}`;
    }
    // Create a new EventSource connection
    // In a real app, you'd likely fetch the URL from an environment config
    this.eventSource = new EventSource(url);

    this.eventSource.onmessage = (event) => {
      this.zone.run(() => {
        try {
          const parsedData = JSON.parse(event.data);
          if (parsedData.action === 'close') {
            this.disconnect();
            return;
          }
          this.messagesSubject.next(parsedData);
        } catch (error) {
          console.error('Failed to parse server event:', error);
        }
      });
    };

    this.eventSource.onerror = (error) => {
      this.zone.run(() => {
        console.error('EventSource failed:', error);
        // You might want to alert the user or attempt to reconnect
        this.messagesSubject.error({
          error: 'Connection Error',
          message: 'Could not connect to the server. Please try again later.'
        });
        this.disconnect();
      });
    };
  }

  sendMessage(msg: { text: string }): void {
    // For SSE, the "sending" is done by establishing the connection
    // with the message as a query parameter.
    this.connect(msg.text);
  }

  disconnect(): void {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
      console.warn('SSE connection closed');
    }
  }
}
