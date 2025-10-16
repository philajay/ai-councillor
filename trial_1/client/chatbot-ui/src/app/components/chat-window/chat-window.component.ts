import { Component, OnInit, OnDestroy, ChangeDetectorRef, Input, ViewChildren, ElementRef, AfterViewChecked, QueryList } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Subscription } from 'rxjs';
import { MatTabsModule, MatTabChangeEvent } from '@angular/material/tabs';
import { MatBadgeModule } from '@angular/material/badge';
import { MatSnackBarModule } from '@angular/material/snack-bar';

import { MessageListComponent } from '../message-list/message-list.component';
import { MessageFormComponent } from '../message-form/message-form.component';
import { CourseChipsComponent } from '../course-chips/course-chips.component';
import { CourseInfoComponent } from '../course-info/course-info.component';
import { MessageService, Thread } from '../../services/message.service';

@Component({
  selector: 'app-chat-window',
  standalone: true,
  imports: [
    CommonModule,
    MatTabsModule,
    MatBadgeModule,
    MatSnackBarModule,
    MessageListComponent,
    MessageFormComponent,
    CourseChipsComponent,
    CourseInfoComponent,
  ],
  templateUrl: './chat-window.component.html',
  styleUrls: ['./chat-window.component.css'],
})
export class ChatWindowComponent implements OnInit, OnDestroy, AfterViewChecked {
  @ViewChildren('messageListContainer') private messageListContainers!: QueryList<ElementRef>;

  threads: Thread[] = [];
  selectedIndex = 0;
  private messagesSub!: Subscription;
  private previousMessageCounts = new Map<string, number>();
  private tabChanged = false;

  constructor(
    private messageService: MessageService,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    this.threads = this.messageService.getThreads();
    this.selectedIndex = this.threads.findIndex(t => t.id === this.messageService.activeThread.id);
    this.threads.forEach(t => this.previousMessageCounts.set(t.id, t.messages.length));

    this.messagesSub = this.messageService.messagesUpdated.subscribe((threadId) => {
      this.threads = this.messageService.getThreads();
      this.selectedIndex = this.threads.findIndex(t => t.id === threadId);
      this.cdr.detectChanges();
    });
  }

  ngAfterViewChecked(): void {
    let shouldScroll = false;

    // Case 1: Tab was changed by the user
    if (this.tabChanged) {
      shouldScroll = true;
      this.tabChanged = false;
    }

    // Case 2: New message arrived in the currently active thread
    const activeThread = this.messageService.activeThread;
    if (activeThread) {
      const currentMessageCount = activeThread.messages.length;
      const previousMessageCount = this.previousMessageCounts.get(activeThread.id) || 0;

      if (currentMessageCount !== previousMessageCount) {
        shouldScroll = true;
        this.previousMessageCounts.set(activeThread.id, currentMessageCount);
      }
    }

    if (shouldScroll) {
      this.scrollToBottom();
    }
  }

  ngOnDestroy(): void {
    if (this.messagesSub) this.messagesSub.unsubscribe();
  }

  scrollToBottom(): void {
    setTimeout(() => {
      try {
        const container = this.messageListContainers.toArray()[this.selectedIndex];
        if (container) {
          container.nativeElement.scrollTop = container.nativeElement.scrollHeight;
        }
      } catch (err) {
        console.error('Could not scroll to bottom:', err);
      }
    }, 0);
  }

  onTabChange(index: number): void {
    this.selectedIndex = index;
    const threadId = this.threads[index].id;
    this.messageService.setActiveThread(threadId);
    this.tabChanged = true;
  }

  onMessageSent(): void {
    // The message is sent to the active thread, no need to switch tabs here.
  }
}
