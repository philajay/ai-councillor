import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MarkdownComponent } from 'ngx-markdown';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatExpansionModule } from '@angular/material/expansion';

import { MessageService } from '../../services/message.service';

@Component({
  selector: 'app-course-info',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatChipsModule,
    MarkdownComponent,
    MatExpansionModule,
    MatTooltipModule,
  ],
  templateUrl: './course-info.component.html',
  styleUrls: ['./course-info.component.css'],
})
export class CourseInfoComponent implements OnChanges {
  @Input() data: any;
  courses: any[] = [];
  groupedCourses: { stream: string; courses: any[] }[] = [];

  constructor(private messageService: MessageService) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['data'] && this.data) {
      const rawCourses = Array.isArray(this.data) ? this.data : [this.data];
      // Map the 'Course' property to 'course_name'
      this.courses = rawCourses.map(course => ({
        ...course,
        course_name: course.Course || 'Course Details'
      }));
      this.groupCoursesByStream();
    }
  }

  exploreCourse(course: any): void {
    this.messageService.createCourseThread(course);
  }

  private groupCoursesByStream(): void {
    const streamMap = new Map<string, any[]>();
    this.courses.forEach(course => {
      const stream = course.stream || 'Other'; // Default stream if undefined
      if (!streamMap.has(stream)) {
        streamMap.set(stream, []);
      }
      streamMap.get(stream)!.push(course);
    });

    this.groupedCourses = Array.from(streamMap.entries()).map(([stream, courses]) => ({
      stream,
      courses
    }));
  }
}
