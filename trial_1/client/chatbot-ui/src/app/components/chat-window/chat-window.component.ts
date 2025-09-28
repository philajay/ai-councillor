import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Observable } from 'rxjs';
import { MatTabsModule } from '@angular/material/tabs';

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
    MessageListComponent,
    MessageFormComponent,
    CourseChipsComponent,
    CourseInfoComponent,
  ],
  templateUrl: './chat-window.component.html',
  styleUrls: ['./chat-window.component.css'],
})
export class ChatWindowComponent {
  coursesForChips$: Observable<string[] | null>;
  courseInfoData$: Observable<any[] | null>;

  constructor(
    private messageService: MessageService,
    private websocketService: WebsocketService
  ) {
    this.coursesForChips$ = this.messageService.courseChips$;
    this.courseInfoData$ = this.messageService.courseInfo$;
  }

  onCourseSelected(course: string): void {
    const newMessage = `I would like to pursue ${course}`;
    this.messageService.addMessage(newMessage, 'user');
    this.websocketService.sendMessage({ text: newMessage });
  }
}