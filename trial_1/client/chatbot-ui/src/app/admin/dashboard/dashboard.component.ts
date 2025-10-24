import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatGridListModule } from '@angular/material/grid-list';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatGridListModule,
    MatIconModule,
    MatProgressBarModule
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.css'
})
export class DashboardComponent implements OnInit {
  // User Chat Sessions
  totalUserSessions: number = 0;
  avgTimeSpent: number = 0;
  avgInteractions: number = 0;
  hotStatus: number = 0;
  coldStatus: number = 0;

  // Query Categorization
  generalQueries: number = 0;
  admissionQueries: number = 0;
  hostelQueries: number = 0;
  scholarshipQueries: number = 0;

  // Conversions
  inquiries: number = 0;
  enrollments: number = 0;

  ngOnInit(): void {
    // Assign random numbers
    this.totalUserSessions = this.getRandomNumber(1000, 2000);
    this.avgTimeSpent = this.getRandomNumber(5, 15);
    this.avgInteractions = this.getRandomNumber(10, 25);
    this.hotStatus = this.getRandomNumber(50, 200);
    this.coldStatus = this.getRandomNumber(200, 500);

    this.generalQueries = this.getRandomNumber(500, 1000);
    this.admissionQueries = this.getRandomNumber(300, 700);
    this.hostelQueries = this.getRandomNumber(100, 300);
    this.scholarshipQueries = this.getRandomNumber(50, 150);

    this.inquiries = this.getRandomNumber(200, 400);
    this.enrollments = this.getRandomNumber(20, 80);
  }

  private getRandomNumber(min: number, max: number): number {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  }
}
