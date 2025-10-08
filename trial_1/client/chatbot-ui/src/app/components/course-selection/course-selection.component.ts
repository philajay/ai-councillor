import { Component, EventEmitter, Output } from '@angular/core';

@Component({
  selector: 'app-course-selection',
  templateUrl: './course-selection.component.html',
  styleUrls: ['./course-selection.component.css']
})
export class CourseSelectionComponent {
  @Output() courseLevelSelected = new EventEmitter<string>();

  selectCourseLevel(level: string) {
    this.courseLevelSelected.emit(level);
  }
}