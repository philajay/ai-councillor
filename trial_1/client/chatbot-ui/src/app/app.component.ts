import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatWindowComponent } from './components/chat-window/chat-window.component';
import { CourseSelectionComponent } from './components/course-selection/course-selection.component';
import { WebsocketService } from './services/websocket.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, ChatWindowComponent, CourseSelectionComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent {
  courseLevel: string | null = null;

  constructor(private websocketService: WebsocketService) {}

  onCourseLevelSelected(level: string) {
    this.courseLevel = level;
    this.websocketService.setCourseLevel(level);
  }
}
