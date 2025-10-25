import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatChipsModule } from '@angular/material/chips';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

interface SuggestionCategory {
  title: string;
  icon: string;
  questions: string[];
}

@Component({
  selector: 'app-suggestion-chips',
  standalone: true,
  imports: [CommonModule, MatChipsModule, MatCardModule, MatIconModule],
  templateUrl: './suggestion-chips.component.html',
  styleUrls: ['./suggestion-chips.component.css']
})
export class SuggestionChipsComponent {
  @Output() questionSelected = new EventEmitter<string>();

  suggestions: SuggestionCategory[] = [
    {
      title: 'Course Finder',
      icon: 'school',
      questions: [
        'Show me computer engineering course in AI',
        'Compare mechanical and civil engineering.',
        'Show options for 12th pass in arts with 60%'
      ]
    },
    {
      title: 'Scholarships/Loans',
      icon: 'savings',
      questions: [
        'How can I apply for a scholarship?',
        'What are the interest rates for student loans?',
        'Are there any scholarships for international students?'
      ]
    },
    {
      title: 'Infrastructure',
      icon: 'apartment',
      questions: [
        'Tell me about the campus library.',
        'What are the sports facilities like?',
        'Are there on-campus housing options?'
      ]
    }
  ];

  onQuestionClick(question: string) {
    this.questionSelected.emit(question);
  }
}