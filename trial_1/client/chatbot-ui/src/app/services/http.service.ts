import { Injectable, NgZone } from '@angular/core';
import { HttpClient } from '@angular/common/http';
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
  private host = "http://localhost:8080"; // Make this configurable
  //private host = "https://ai-assistant-bot-183228620742.us-central1.run.app"

  constructor(private zone: NgZone, private http: HttpClient) {}

  private getSessionId(): string {
    // let sessionId = localStorage.getItem('chatSessionId');
    // if (!sessionId) {
    //   sessionId = crypto.randomUUID();
    //   localStorage.setItem('chatSessionId', sessionId);
    // }
    // return sessionId;
    return crypto.randomUUID();
  }

  setCourseLevel(level: string) {
    this.courseLevel = level;
  }

  warmUpServer() {
    this.http.get(`${this.host}/hello_world`).subscribe({
      next: (res) => console.log('Server warmed up:', res),
      error: (err) => console.error('Error warming up server:', err)
    });
  }

  connect(message: string): void {
    // Disconnect any existing connection
    this.disconnect();

    const sessionId = this.getSessionId();
    let url = `${this.host}/chat?text=${encodeURIComponent(message)}&sessionId=${sessionId}`;
    if (this.courseLevel) {
      url += `&courseLevel=${encodeURIComponent(this.courseLevel)}`;
    }
    // Create a new EventSource connection
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
        this.messagesSubject.error({
          error: 'Connection Error',
          message: 'Could not connect to the server. Please try again later.'
        });
        this.disconnect();
      });
    };
  }

  sendMessage(msg: { text: string }): void {
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
