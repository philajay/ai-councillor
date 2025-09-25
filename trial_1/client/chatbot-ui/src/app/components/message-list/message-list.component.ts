import { Component, OnInit, ElementRef, AfterViewChecked, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Message, MessageService } from '../../services/message.service';
import { MarkdownComponent } from 'ngx-markdown';
import { Subscription } from 'rxjs';
import { CourseChipsComponent } from '../course-chips/course-chips.component';
import { CourseInfoComponent } from '../course-info/course-info.component';
import { WebsocketService } from '../../services/websocket.service';

@Component({
  selector: 'app-message-list',
  standalone: true,
  imports: [CommonModule, MarkdownComponent, CourseChipsComponent, CourseInfoComponent],
  templateUrl: './message-list.component.html',
  styleUrls: ['./message-list.component.css']
})
export class MessageListComponent implements OnInit, AfterViewChecked, OnDestroy {
  messages: Message[] = [];
  private shouldScroll = false;
  private subscription!: Subscription;

  constructor(
    private messageService: MessageService,
    private el: ElementRef,
    private websocketService: WebsocketService 
  ) {}

  ngOnInit(): void {
    this.subscription = this.messageService.messagesUpdated.subscribe(() => {
      this.messages = this.messageService.messages;
      this.shouldScroll = true;
    });
    this.messages = this.messageService.messages;
  }

  ngAfterViewChecked(): void {
    if (this.shouldScroll) {
      this.scrollToBottom();
      this.shouldScroll = false;
    }
  }

  ngOnDestroy(): void {
    if (this.subscription) {
      this.subscription.unsubscribe();
    }
  }

  private scrollToBottom(): void {
    try {
      this.el.nativeElement.scroll({
        top: this.el.nativeElement.scrollHeight,
        left: 0,
        behavior: 'smooth'
      });
    } catch (err) {
      console.error('Could not scroll to bottom:', err);
    }
  }

  onCourseSelected(course: any) {
    let newMessage = `I would like to pursue ${course}`
    this.messageService.addMessage(newMessage, 'user');
    this.websocketService.sendMessage({ text: newMessage });
  }
}