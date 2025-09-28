import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MarkdownComponent } from 'ngx-markdown';
import { MatExpansionModule } from '@angular/material/expansion';

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
  ],
  templateUrl: './course-info.component.html',
  styleUrls: ['./course-info.component.css'],
})
export class CourseInfoComponent implements OnChanges {
  @Input() data: any;
  courses: any[] = [];
  groupedCourses: { stream: string; courses: any[] }[] = [];

  constructor() {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['data'] && this.data) {
      this.courses = Array.isArray(this.data) ? this.data : [this.data];
      this.groupCoursesByStream();
    }
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
