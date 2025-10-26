import { Injectable, NgZone } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Subject } from 'rxjs';
import { ServerEvent } from '../models/server-event.model';
import { environment } from '../../environments/environment';
import { Auth, onAuthStateChanged } from '@angular/fire/auth';
import { Firestore, doc, getDoc, setDoc } from '@angular/fire/firestore';

@Injectable({
  providedIn: 'root'
})
export class HttpService {
  private abortController: AbortController | null = null;
  private messagesSubject = new Subject<ServerEvent>();
  public messages$ = this.messagesSubject.asObservable();
  private courseLevel: string | null = null;
  private host = environment.apiUrl;
  private chatSessionId: string | null = null;
  //private host = "https://ai-assistant-bot-183228620742.us-central1.run.app"

  constructor(
    private zone: NgZone,
    private http: HttpClient,
    private auth: Auth,
    private firestore: Firestore
  ) {
    // Invalidate cache on user logout
    onAuthStateChanged(this.auth, (user) => {
      if (!user) {
        this.chatSessionId = null;
      }
    });
  }

  private async getSessionId(): Promise<string> {
    if (this.chatSessionId) {
      return this.chatSessionId;
    }

    const user = this.auth.currentUser;
    if (!user) {
      throw new Error('User not authenticated. Cannot create a chat session.');
    }
    
    const userDocRef = doc(this.firestore, 'users', user.uid);
    const docSnap = await getDoc(userDocRef);

    if (docSnap.exists() && docSnap.data()['session']) {
      this.chatSessionId = docSnap.data()['session'];
      return this.chatSessionId!;
    } else {
      const newSessionId = crypto.randomUUID();
      await setDoc(userDocRef, { session: newSessionId }, { merge: true });
      this.chatSessionId = newSessionId;
      return newSessionId;
    }
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

  private async connect(url: string, body: any): Promise<void> {
    this.disconnect();
    this.abortController = new AbortController();
    const signal = this.abortController.signal;

    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        signal,
      });

      if (!response.body) {
        throw new Error('Response body is null');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      const processStream = async () => {
        while (true) {
          const { done, value } = await reader.read();
          if (done) {
            break;
          }

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n\n');

          for (const line of lines) {
            if (line.startsWith('data:')) {
              const data = line.substring(5).trim();
              this.zone.run(() => {
                try {
                  const parsedData = JSON.parse(data);
                  if (parsedData.action === 'close') {
                    this.disconnect();
                    return;
                  }
                  this.messagesSubject.next(parsedData);
                } catch (error) {
                  console.error('Failed to parse server event:', error);
                }
              });
            }
          }
        }
      };

      await processStream();

    } catch (error) {
      if (signal.aborted) {
        console.log('Fetch request aborted.');
        return;
      }
      this.zone.run(() => {
        console.error('Fetch API failed:', error);
        this.messagesSubject.error({
          error: 'Connection Error',
          message: 'Could not connect to the server. Please try again later.'
        });
        this.disconnect();
      });
    }
  }

  async sendMessage(msg: { text: string }): Promise<void> {
    const sessionId = await this.getSessionId();
    const url = `${this.host}/chat`;
    const body = {
      text: msg.text,
      sessionId: sessionId,
      courseLevel: this.courseLevel
    };
    this.connect(url, body);
  }

  async sendCourseMessage(msg: { text: string, courseId: string }): Promise<void> {
    const sessionId = await this.getSessionId();
    const url = `${this.host}/get_course`;
    const body = {
      text: msg.text,
      sessionId: sessionId,
      courseId: msg.courseId
    };
    this.connect(url, body);
  }

  disconnect(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
      console.warn('SSE connection closed');
    }
  }

  categorizeLead(): void {
    const user = this.auth.currentUser;
    if (user) {
      const url = `https://ai-assistant-bot-183228620742.us-central1.run.app/categorize_lead/${user.uid}`;
      this.http.get(url).subscribe({
        next: (res) => console.log('categorize_lead response:', res),
        error: (err) => console.error('categorize_lead error:', err)
      });
    } else {
      console.error('User not authenticated. Cannot categorize lead.');
    }
  }
}
