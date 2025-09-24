import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatChipsModule, MatChipListboxChange } from '@angular/material/chips';

@Component({
  selector: 'app-course-chips',
  templateUrl: './course-chips.component.html',
  styleUrls: ['./course-chips.component.css'],
  standalone: true,
  imports: [MatChipsModule]
})
export class CourseChipsComponent {
  @Input() courses: string[] = [];
  @Output() courseSelected = new EventEmitter<string>();

  onChipSelectionChange(event: MatChipListboxChange) {
    this.courseSelected.emit(event.value);
  }
}