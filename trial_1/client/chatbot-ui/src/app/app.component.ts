import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChatWindowComponent } from './components/chat-window/chat-window.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, ChatWindowComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent {}
