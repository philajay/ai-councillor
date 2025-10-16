import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MarkdownComponent } from 'ngx-markdown';
import { MessageService } from '../../services/message.service';

@Component({
  selector: 'app-course-details',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MarkdownComponent,
  ],
  templateUrl: './course-details.component.html',
  styleUrl: './course-details.component.css'
})
export class CourseDetailsComponent implements OnInit {
  @Input() course: any;

  // A more generic structure for action chips
  actionChips: { text: string, type: 'message' | 'open_tab', payload: any }[] = [];

  constructor(private messageService: MessageService) {}

  ngOnInit(): void {
    // const initialMessage = `Why should I choose the ${this.course.name} course from your university?`;
    // this.messageService.addMessage(initialMessage, 'user');

    // Initialize action chips, potentially based on course data in the future
    this.actionChips = [
      { text: 'Explore University', type: 'open_tab', payload: { tab: 'university', id: this.course.universityId || 'U123' } },
      { text: 'View Hostel Options', type: 'open_tab', payload: { tab: 'hostels', id: this.course.universityId || 'U123' } },
      { text: 'Tell me about the faculty', type: 'message', payload: `Tell me about the faculty for ${this.course.name}` },
      { text: 'Scholarship', type: 'message', payload: `Are there any scholarships available for ${this.course.name}?` },
      { text: 'Loan Facilities', type: 'message', payload: `Are there any loan facilities available for ${this.course.name}?` },
      { text: 'Register Now', type: 'open_tab', payload: { tab: 'register', courseId: this.course.id } }
    ];
  }

  handleChipClick(chip: { text: string, type: 'message' | 'open_tab', payload: any }): void {
    switch (chip.type) {
      case 'message':
        this.messageService.addMessage(chip.payload, 'user');
        break;
      case 'open_tab':
        // For now, we'll just log this. This would eventually call a service
        // to open a new tab in the UI.
        console.log('Opening tab with payload:', chip.payload);
        break;
      default:
        console.error('Unknown chip action type:', chip.type);
    }
  }
}
