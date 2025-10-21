import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet } from '@angular/router';
import { HttpService } from './services/http.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, RouterOutlet],
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
