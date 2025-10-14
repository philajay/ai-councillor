import {
  Component,
  OnInit,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Message, MessageService } from '../../services/message.service';
import { MarkdownComponent } from 'ngx-markdown';
import { CourseInfoComponent } from '../course-info/course-info.component';
import { HttpService } from '../../services/http.service';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-message-list',
  standalone: true,
  imports: [CommonModule, MarkdownComponent, CourseInfoComponent, MatProgressSpinnerModule, MatButtonModule],
  templateUrl: './message-list.component.html',
  styleUrls: ['./message-list.component.css'],
})
export class MessageListComponent implements OnInit {

  constructor(
    public messageService: MessageService,
    private httpService: HttpService
  ) {}

  ngOnInit(): void {
  }

  onRetry(message: Message): void {
    if (message.originalText) {
      const errorMsgIndex = this.messageService.messages.findIndex(
        (m) => m.isError && m.originalText === message.originalText
      );
      if (errorMsgIndex > -1) {
        this.messageService.messages.splice(errorMsgIndex, 1);
      }
      this.httpService.sendMessage({ text: message.originalText });
    }
  }
  loadCGC(){
    window.open('https://cgcuet.cgcuniversity.in/', '_blank')
  }
}
