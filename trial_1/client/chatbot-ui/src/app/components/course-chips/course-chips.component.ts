import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-course-chips',
  standalone: true,
  imports: [CommonModule, MatIconModule],
  templateUrl: './course-chips.component.html',
  styleUrls: ['./course-chips.component.css'],
})
export class CourseChipsComponent {
  @Input() courses: string[] = [];
  @Output() showCourses = new EventEmitter<string>();
  @Output() showCareers = new EventEmitter<string>();

  flipped = new Set<string>();

  toggleFlip(course: string): void {
    if (this.flipped.has(course)) {
      this.flipped.delete(course);
    } else {
      this.flipped.add(course);
    }
  }

  onShowCourses(course: string): void {
    this.showCourses.emit(course);
  }

  onShowCareers(course: string): void {
    this.showCareers.emit(course);
  }
}