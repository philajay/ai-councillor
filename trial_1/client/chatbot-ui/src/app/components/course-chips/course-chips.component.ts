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
  @Output() courseSelected = new EventEmitter<string>();

  isExpanded = true;

  onChipClick(course: string): void {
    this.courseSelected.emit(course);
  }

  toggle(): void {
    this.isExpanded = !this.isExpanded;
  }
}