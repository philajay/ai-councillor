import { Component } from '@angular/core';
import { MessageListComponent } from '../message-list/message-list.component';
import { MessageFormComponent } from '../message-form/message-form.component';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-chat-window',
  standalone: true,
  imports: [CommonModule, MessageListComponent, MessageFormComponent],
  templateUrl: './chat-window.component.html',
  styleUrls: ['./chat-window.component.css']
})
export class ChatWindowComponent {

}