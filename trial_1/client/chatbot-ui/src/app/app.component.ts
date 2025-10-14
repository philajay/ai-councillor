import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatWindowComponent } from './components/chat-window/chat-window.component';
import { CourseSelectionComponent } from './components/course-selection/course-selection.component';
import { HttpService } from './services/http.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, ChatWindowComponent, CourseSelectionComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent {
  courseLevel: string | null = null;

  constructor(private httpService: HttpService) {}

  onCourseLevelSelected(level: string) {
    this.courseLevel = level;
    this.httpService.setCourseLevel(level);
  }
}
