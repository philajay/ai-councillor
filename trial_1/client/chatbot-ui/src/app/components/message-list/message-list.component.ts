import {
  Component,
  OnInit,
  ElementRef,
  OnDestroy,
  ViewChild,
  AfterViewInit,
  ViewChildren,
  QueryList,
  AfterViewChecked,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Message, MessageService } from '../../services/message.service';
import { MarkdownComponent } from 'ngx-markdown';
import { Subscription } from 'rxjs';
import { CourseInfoComponent } from '../course-info/course-info.component';
import { HttpService } from '../../services/http.service';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-message-list',
  standalone: true,
  imports: [CommonModule, MarkdownComponent, CourseInfoComponent, MatProgressSpinnerModule, MatButtonModule],
  templateUrl: './message-list.component.html',
  styleUrls: ['./message-list.component.css'],
})
export class MessageListComponent implements OnInit, OnDestroy, AfterViewInit, AfterViewChecked {
  @ViewChild('scrollMe') private messageContainer!: ElementRef;
  @ViewChildren('message') public messages!: QueryList<any>;
  private messagesSubscription!: Subscription;
  private messageCount = 0;

  constructor(
    public messageService: MessageService,
    private httpService: HttpService
  ) {}

  ngOnInit(): void {
    this.messagesSubscription = this.messageService.messagesUpdated.subscribe(() => {
      this.messageCount = this.messageService.messages.length;
    });
  }

  ngAfterViewInit(): void {
    this.messages.changes.subscribe(this.scrollToBottom);
  }

  ngAfterViewChecked(): void {
    this.scrollToBottom();
  }

  ngOnDestroy(): void {
    if (this.messagesSubscription) {
      this.messagesSubscription.unsubscribe();
    }
  }

  private scrollToBottom = () => {
    if (this.messageContainer && this.messageContainer.nativeElement) {
      try {
        this.messageContainer.nativeElement.scrollTop = this.messageContainer.nativeElement.scrollHeight;
      } catch (err) {
        console.error('Could not scroll to bottom:', err);
      }
    }
  };

  onRetry(message: Message): void {
    if (message.originalText) {
      // Find the error message that corresponds to this retry attempt and remove it
      const errorMsgIndex = this.messageService.messages.findIndex(
        (m) => m.isError && m.originalText === message.originalText
      );
      if (errorMsgIndex > -1) {
        this.messageService.messages.splice(errorMsgIndex, 1);
      }
      // Resend the original message
      this.httpService.sendMessage({ text: message.originalText });
    }
  }
}
