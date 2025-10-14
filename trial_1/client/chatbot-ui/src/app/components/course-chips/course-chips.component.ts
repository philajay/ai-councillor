import { Component, Input, Output, EventEmitter, ElementRef, HostListener } from '@angular/core';
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

  isExpanded = false;

  constructor(private elementRef: ElementRef) {}

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    if (!this.elementRef.nativeElement.contains(event.target) && this.isExpanded) {
      this.isExpanded = false;
    }
  }

  onChipClick(course: string): void {
    this.courseSelected.emit(course);
    this.isExpanded = false; // Also collapse after selection
  }

  toggle(event: MouseEvent): void {
    event.stopPropagation(); // Prevent the document click listener from firing immediately
    this.isExpanded = !this.isExpanded;
  }
}