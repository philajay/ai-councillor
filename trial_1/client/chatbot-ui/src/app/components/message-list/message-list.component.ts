import { Component, OnInit, ElementRef, AfterViewChecked, OnDestroy } from '@angular/core';
import { Message, MessageService } from '../../services/message.service';
import { CommonModule } from '@angular/common';
import { MarkdownComponent } from 'ngx-markdown';
import { Subscription } from 'rxjs';

@Component({
  selector: 'app-message-list',
  standalone: true,
  imports: [CommonModule, MarkdownComponent],
  templateUrl: './message-list.component.html',
  styleUrls: ['./message-list.component.css']
})
export class MessageListComponent implements OnInit, AfterViewChecked, OnDestroy {
  messages: Message[] = [];
  private shouldScroll = false;
  private messagesSubscription: Subscription;

  constructor(
    private messageService: MessageService,
    private el: ElementRef
  ) {}

  ngOnInit(): void {
    this.messages = this.messageService.messages;
    this.messagesSubscription = this.messageService.messagesUpdated.subscribe(() => {
      this.shouldScroll = true;
    });
  }

  ngAfterViewChecked(): void {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  ngOnDestroy(): void {
    if (this.messagesSubscription) {
      this.messagesSubscription.unsubscribe();
    }
  }

  private scrollToBottom(): void {
    try {
      this.el.nativeElement.scrollTop = this.el.nativeElement.scrollHeight;
    } catch (err) {
      console.error('Could not scroll to bottom:', err);
    }
  }
}