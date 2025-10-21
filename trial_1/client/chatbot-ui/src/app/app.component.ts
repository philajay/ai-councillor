import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatWindowComponent } from './components/chat-window/chat-window.component';
import { CourseSelectionComponent } from './components/course-selection/course-selection.component';
import { HttpService } from './services/http.service';
import { LoginComponent } from './auth/login/login.component';
import { Auth, onAuthStateChanged } from '@angular/fire/auth';
import { User } from 'firebase/auth';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, ChatWindowComponent, CourseSelectionComponent, LoginComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent {
  courseLevel: string | null = null;
  user: User | null = null;

  constructor(private httpService: HttpService, private auth: Auth) {
    onAuthStateChanged(this.auth, (user) => {
      this.user = user;
    });
  }

  onCourseLevelSelected(level: string) {
    this.courseLevel = level;
    this.httpService.setCourseLevel(level);
  }
}
