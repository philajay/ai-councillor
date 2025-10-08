import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { HttpService } from '../../services/http.service';

@Component({
  selector: 'app-course-selection',
  templateUrl: './course-selection.component.html',
  styleUrls: ['./course-selection.component.css']
})
export class CourseSelectionComponent implements OnInit {
  @Output() courseLevelSelected = new EventEmitter<string>();

  constructor(private httpService: HttpService) {}

  ngOnInit(): void {
    this.httpService.warmUpServer();
  }

  selectCourseLevel(level: string) {
    this.courseLevelSelected.emit(level);
  }
}