import { Component, Input, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MarkdownComponent } from 'ngx-markdown';
import { Router } from '@angular/router';
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
  actionChips: { text: string, type: 'message' | 'open_tab' | 'navigate', payload: any }[] = [];

  constructor(private messageService: MessageService, private router: Router) {}

  ngOnInit(): void {
    // const initialMessage = `Why should I choose the ${this.course.name} course from your university?`;
    // this.messageService.addMessage(initialMessage, 'user');

    // Initialize action chips, potentially based on course data in the future
    this.actionChips = [
      { text: 'Explore University', type: 'open_tab', payload: { tab: 'university', id: "university" } },
      { text: 'View Hostel Options', type: 'open_tab', payload: { tab: 'hostels', id: 'hostels' } },
      { text: 'Tell me about the faculty', type: 'message', payload: `Tell me about the faculty for ${this.course.name}` },
      { text: 'Scholarship', type: 'message', payload: `Are there any scholarships available for ${this.course.name}?` },
      { text: 'Loan Facilities', type: 'message', payload: `Are there any loan facilities available for ${this.course.name}?` },
      { text: 'Register Now', type: 'navigate', payload: {
          route: '/upload-documents',
          tags: ['aadhaar-front', 'aadhaar-back'],
          courseId: this.course.id,
          courseName: this.course.name
        }
      }
    ];
  }

  handleChipClick(chip: { text: string, type: 'message' | 'open_tab' | 'navigate', payload: any }): void {
    switch (chip.type) {
      case 'message':
        this.messageService.addMessage(chip.payload, 'user');
        break;
      case 'open_tab':
        switch (chip.payload.tab) {
          case 'university':
          case 'hostels':
            this.messageService.createGalleryThread(chip.payload.id, chip.text);
            break;
          default:
            console.log('Opening tab with payload:', chip.payload);
            break;
        }
        break;
      case 'navigate':
        this.router.navigate([chip.payload.route], { state: {
            tags: chip.payload.tags,
            courseId: chip.payload.courseId,
            courseName: chip.payload.courseName
          }
        });
        break;
      default:
        console.error('Unknown chip action type:', chip.type);
    }
  }
}
