import { Component, Input, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-gallery',
  standalone: true,
  imports: [CommonModule, MatButtonModule, MatIconModule],
  templateUrl: './gallery.component.html',
  styleUrl: './gallery.component.css'
})
export class GalleryComponent implements OnInit, OnDestroy {
  @Input() data: any;

  images = [
    'https://www.cgcuniversity.in/public/course/assets/images/support/green_panther.webp',
    'https://www.cgcuniversity.in/public/course/assets/images/support/rockers.webp',
    'https://www.cgcuniversity.in/public/course/assets/images/support/cgc_fit.webp',
    'https://www.cgcuniversity.in/public/course/assets/images/support/art_master.webp'
  ];
  currentIndex = 0;
  private intervalId: any;

  ngOnInit(): void {
    this.intervalId = setInterval(() => {
      this.next();
    }, 1000);
  }

  ngOnDestroy(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId);
    }
  }

  previous(): void {
    this.currentIndex = (this.currentIndex > 0) ? this.currentIndex - 1 : this.images.length - 1;
  }

  next(): void {
    this.currentIndex = (this.currentIndex < this.images.length - 1) ? this.currentIndex + 1 : 0;
  }

  get currentImage(): string {
    return this.images[this.currentIndex];
  }
}
