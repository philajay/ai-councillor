import {
  Component,
  OnInit,
  ElementRef,
  OnDestroy,
  ViewChild,
  AfterViewInit,
  ViewChildren,
  QueryList,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Message, MessageService } from '../../services/message.service';
import { MarkdownComponent } from 'ngx-markdown';
import { Subscription } from 'rxjs';
import { CourseInfoComponent } from '../course-info/course-info.component';
import { WebsocketService } from '../../services/websocket.service';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

@Component({
  selector: 'app-message-list',
  standalone: true,
  imports: [
    CommonModule,
    MarkdownComponent,
    CourseInfoComponent,
    MatButtonModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './message-list.component.html',
  styleUrls: ['./message-list.component.css'],
})
export class MessageListComponent
  implements OnInit, OnDestroy, AfterViewInit
{
  @ViewChild('scrollMe') private myScrollContainer!: ElementRef;
  @ViewChildren('messageEl') private messageElements!: QueryList<ElementRef>;

  messages: Message[] = [];
  private messagesSubscription!: Subscription;
  private viewChildrenSubscription!: Subscription;

  constructor(
    private messageService: MessageService,
    private websocketService: WebsocketService
  ) {}

  ngOnInit(): void {
    this.messagesSubscription = this.messageService.messagesUpdated.subscribe(() => {
      this.messages = this.messageService.messages;
    });
    this.messages = this.messageService.messages;
  }

  ngAfterViewInit(): void {
    this.scrollToBottom(); // Initial scroll
    this.viewChildrenSubscription = this.messageElements.changes.subscribe(() => {
      this.scrollToBottom();
    });
  }

  ngOnDestroy(): void {
    if (this.messagesSubscription) {
      this.messagesSubscription.unsubscribe();
    }
    if (this.viewChildrenSubscription) {
      this.viewChildrenSubscription.unsubscribe();
    }
  }

  private scrollToBottom(): void {
    try {
      // Using setTimeout to make sure the scroll happens after the view is updated
      setTimeout(() => {
        this.myScrollContainer.nativeElement.scrollTop =
          this.myScrollContainer.nativeElement.scrollHeight;
      }, 0);
    } catch (err) {
      console.error('Could not scroll to bottom:', err);
    }
  }

  onRetry(message: Message): void {
    if (message.originalText) {
      this.messageService.addMessage(message.originalText, 'user');
      this.websocketService.sendMessage({ text: message.originalText });
    }
  }
}
