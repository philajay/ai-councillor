import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MessageListComponent } from './components/message-list/message-list.component';
import { MessageFormComponent } from './components/message-form/message-form.component';
import { CourseChipsComponent } from './components/course-chips/course-chips.component';
import { MessageService } from './services/message.service';
import { WebsocketService } from './services/websocket.service';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [
    CommonModule,
    MessageListComponent,
    MessageFormComponent,
    CourseChipsComponent,
  ],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent implements OnInit {
  coursesForChips$: Observable<string[] | null>;

  constructor(
    private messageService: MessageService,
    private websocketService: WebsocketService
  ) {
    this.coursesForChips$ = this.messageService.courseChips$;
  }

  ngOnInit(): void {}

  onCourseSelected(course: string): void {
    const newMessage = `I would like to pursue ${course}`;
    this.messageService.addMessage(newMessage, 'user');
    this.websocketService.sendMessage({ text: newMessage });
  }
}
