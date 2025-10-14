import { Component, OnInit, OnDestroy, ChangeDetectorRef, Input, ViewChild, ElementRef, AfterViewChecked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Observable, Subscription } from 'rxjs';
import { skip, tap, scan } from 'rxjs/operators';
import { MatTabsModule, MatTabChangeEvent, MatTabGroup } from '@angular/material/tabs';
import { MatBadgeModule } from '@angular/material/badge';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

import { MessageListComponent } from '../message-list/message-list.component';
import { MessageFormComponent } from '../message-form/message-form.component';
import { CourseChipsComponent } from '../course-chips/course-chips.component';
import { CourseInfoComponent } from '../course-info/course-info.component';
import { MessageService } from '../../services/message.service';
import { HttpService } from '../../services/http.service';

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
  @Input() courseLevel!: string;
  @ViewChild('messageListContainer') private messageListContainer!: ElementRef;

  courseInfoData$: Observable<any[] | null>;
  showCourseInfoBadge = false;
  selectedIndex = 0;

  private courseInfoSub!: Subscription;
  private previousMessageCount = 0;

  constructor(
    private messageService: MessageService,
    private httpService: HttpService,
    private snackBar: MatSnackBar,
    private cdr: ChangeDetectorRef
  ) {
    this.courseInfoData$ = this.messageService.courseInfo$;
  }

  ngOnInit(): void {
    this.previousMessageCount = this.messageService.messages.length;
    this.courseInfoSub = this.messageService.courseInfo$.pipe(skip(1)).subscribe(data => {
      if (data && data.length > 0) {
        this.showCourseInfoBadge = true;
        this.snackBar.open(`${data.length} courses found. Click on the Course Info tab for details.`, 'Dismiss');
        this.cdr.markForCheck();
      }
    });
  }

  ngAfterViewChecked(): void {
    if (this.messageService.messages.length !== this.previousMessageCount) {
      this.scrollToBottom();
      this.previousMessageCount = this.messageService.messages.length;
    }
  }

  ngOnDestroy(): void {
    if (this.courseInfoSub) this.courseInfoSub.unsubscribe();
  }

  scrollToBottom(): void {
    setTimeout(() => {
      try {
        this.messageListContainer.nativeElement.scrollTop = this.messageListContainer.nativeElement.scrollHeight;
      } catch (err) {
        console.error('Could not scroll to bottom:', err);
      }
    }, 0);
  }

  onTabChange(event: MatTabChangeEvent): void {
    if (event.index === 1) {
      this.showCourseInfoBadge = false;
    }
  }

  onMessageSent(): void {
    this.selectedIndex = 0;
  }
}
