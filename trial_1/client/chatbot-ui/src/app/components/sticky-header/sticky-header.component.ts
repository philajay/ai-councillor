import { Component, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-sticky-header',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './sticky-header.component.html',
  styleUrls: ['./sticky-header.component.css']
})
export class StickyHeaderComponent {
  @Output() headerClick = new EventEmitter<void>();

  onClick(): void {
    this.headerClick.emit();
  }
}
