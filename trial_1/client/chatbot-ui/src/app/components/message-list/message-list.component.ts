import {
  Component,
  Input,
  ViewChild,
  ElementRef,
  QueryList,
  ViewChildren,
  ChangeDetectorRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Message, MessageService } from '../../services/message.service';
import { MarkdownComponent } from 'ngx-markdown';
import { CourseInfoComponent } from '../course-info/course-info.component';
import { CourseChipsComponent } from '../course-chips/course-chips.component';
import { HttpService } from '../../services/http.service';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { IntersectionObserverDirective } from '../../directives/intersection-observer.directive';
import { StickyHeaderComponent } from '../sticky-header/sticky-header.component';
import { CourseDetailsComponent } from '../course-details/course-details.component';
import { MatIconModule } from '@angular/material/icon';
import { GalleryComponent } from '../gallery/gallery.component';
import { SuggestionChipsComponent } from '../suggestion-chips/suggestion-chips.component';

@Component({
  selector: 'app-message-list',
  standalone: true,
  imports: [CommonModule, MarkdownComponent, CourseInfoComponent, CourseChipsComponent, MatProgressSpinnerModule, MatButtonModule, IntersectionObserverDirective, StickyHeaderComponent, CourseDetailsComponent, MatIconModule, GalleryComponent, SuggestionChipsComponent],
  templateUrl: './message-list.component.html',
  styleUrls: ['./message-list.component.css'],
})
export class MessageListComponent {
  @Input() messages: Message[] = [];
  @ViewChild('scrollMe') private scrollContainer!: ElementRef;
  @ViewChildren('messageEl') private messageElements!: QueryList<ElementRef>;

  showStickyHeader = false;

  constructor(
    private messageService: MessageService,
    private httpService: HttpService,
    private cdr: ChangeDetectorRef
  ) {}

  onVisibilityChange(isVisible: boolean): void {
    this.showStickyHeader = !isVisible;
  }

  scrollToCourseChips(): void {
    const courseChipsElement = this.messageElements.find(el => el.nativeElement.querySelector('app-course-chips'));
    if (courseChipsElement) {
      courseChipsElement.nativeElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }

  onShowCourses(course: string): void {
    const newMessage = `Show me courses in ${course}`;
    this.messageService.addMessage(newMessage, 'user');
  }

  onShowCareers(course: string): void {
    const newMessage = `What are the career options for ${course}?`;
    this.messageService.addMessage(newMessage, 'user');
  }

  onShowFees(course: string): void {
    const newMessage = `What are the fees for ${course}?`;
    this.messageService.addMessage(newMessage, 'user');
  }

  onShowPlacements(course: string): void {
    const newMessage = `What are the placement details for ${course}?`;
    this.messageService.addMessage(newMessage, 'user');
  }

  onQuestionSelected(question: string): void {
    this.messageService.addMessage(question, 'user');
  }

  onRetry(message: Message): void {
    if (message.originalText) {
      const errorMsgIndex = this.messages.findIndex(
        (m) => m.isError && m.originalText === message.originalText
      );
      if (errorMsgIndex > -1) {
        this.messages.splice(errorMsgIndex, 1);
      }
      this.httpService.sendMessage({ text: message.originalText });
    }
  }
  loadCGC(){
    window.open('https://cgcuet.cgcuniversity.in/', '_blank')
  }

  cleanMarkdown(text: string): string {
    if (!text) {
      return '';
    }
    // This regex splits by both '\\n' and '\n'
    return text.split(/\\n|\n/).map(line => line.trim()).join('\n');
  }
}
