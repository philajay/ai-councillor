import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Observable, Subscription } from 'rxjs';
import { skip } from 'rxjs/operators';
import { MatTabsModule, MatTabChangeEvent } from '@angular/material/tabs';
import { MatBadgeModule } from '@angular/material/badge';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { MessageListComponent } from '../message-list/message-list.component';
import { MessageFormComponent } from '../message-form/message-form.component';
import { CourseChipsComponent } from '../course-chips/course-chips.component';
import { CourseInfoComponent } from '../course-info/course-info.component';
import { MessageService } from '../../services/message.service';
import { WebsocketService } from '../../services/websocket.service';

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
export class ChatWindowComponent implements OnInit, OnDestroy {
  coursesForChips$: Observable<string[] | null>;
  courseInfoData$: Observable<any[] | null>;
  showCourseInfoBadge = false;
  private courseInfoSub!: Subscription;

  constructor(
    private messageService: MessageService,
    private websocketService: WebsocketService,
    private snackBar: MatSnackBar,
    private cdr: ChangeDetectorRef
  ) {
    this.coursesForChips$ = this.messageService.courseChips$;
    this.courseInfoData$ = this.messageService.courseInfo$;
  }

  ngOnInit(): void {
    this.courseInfoSub = this.messageService.courseInfo$.pipe(skip(1)).subscribe(data => {
      if (data && data.length > 0) {
        this.showCourseInfoBadge = true;
        this.snackBar.open(`${data.length} courses found. Click on the Course Info tab for details.`, 'Dismiss', {
        });
        this.cdr.markForCheck();
      }
    });
  }

  ngOnDestroy(): void {
    if (this.courseInfoSub) {
      this.courseInfoSub.unsubscribe();
    }
  }

  onCourseSelected(course: string): void {
    const newMessage = `I would like to pursue ${course}`;
    this.messageService.addMessage(newMessage, 'user');
    this.websocketService.sendMessage({ text: newMessage });
  }

  onTabChange(event: MatTabChangeEvent): void {
    if (event.index === 1) {
      this.showCourseInfoBadge = false;
    }
  }
}
