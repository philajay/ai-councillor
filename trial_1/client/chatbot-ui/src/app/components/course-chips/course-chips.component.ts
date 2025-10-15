import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-course-chips',
  standalone: true,
  imports: [CommonModule, MatIconModule],
  templateUrl: './course-chips.component.html',
  styleUrls: ['./course-chips.component.css'],
})
export class CourseChipsComponent implements OnInit {
  @Input() courses: string[] = [];
  @Output() showCourses = new EventEmitter<string>();
  @Output() showCareers = new EventEmitter<string>();
  @Output() showFees = new EventEmitter<string>();
  @Output() showPlacements = new EventEmitter<string>();

  courseIcons = new Map<string, string>();
  private icons = ['beaker.svg', 'graduation-cap.svg', 'lightbulb.svg', 'atom.svg'];
  flipped = new Set<string>();

  ngOnInit(): void {
    this.assignIcons();
  }

  toggleFlip(course: string): void {
    if (this.flipped.has(course)) {
      this.flipped.delete(course);
    } else {
      this.flipped.add(course);
    }
  }

  private assignIcons(): void {
    this.courseIcons.clear();
    this.courses.forEach(course => {
      const iconIndex = Math.floor(Math.random() * this.icons.length);
      this.courseIcons.set(course, `assets/${this.icons[iconIndex]}`);
    });
  }

  onShowCourses(course: string): void {
    this.showCourses.emit(course);
  }

  onShowCareers(course: string): void {
    this.showCareers.emit(course);
  }

  onShowFees(course: string): void {
    this.showFees.emit(course);
  }

  onShowPlacements(course: string): void {
    this.showPlacements.emit(course);
  }
}