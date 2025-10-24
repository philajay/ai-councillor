import { Component, AfterViewInit, ElementRef, ViewChild, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

interface Line {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

@Component({
  selector: 'app-workflow',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule
  ],
  templateUrl: './workflow.component.html',
  styleUrl: './workflow.component.css'
})
export class WorkflowComponent implements AfterViewInit {
  @ViewChild('workflowContainer') container!: ElementRef;
  lines: Line[] = [];

  ngAfterViewInit(): void {
    // Use requestAnimationFrame to ensure the view is fully rendered before calculating positions
    requestAnimationFrame(() => this.drawConnectors());
  }

  @HostListener('window:resize')
  onResize(): void {
    this.drawConnectors();
  }

  private drawConnectors(): void {
    this.lines = [];
    if (!this.container) return;

    const containerRect = this.container.nativeElement.getBoundingClientRect();

    const getCoords = (elementId: string) => {
      const el = document.getElementById(elementId);
      if (!el) return null;
      const rect = el.getBoundingClientRect();
      return {
        top: rect.top - containerRect.top,
        bottom: rect.bottom - containerRect.top,
        left: rect.left - containerRect.left,
        right: rect.right - containerRect.left,
        width: rect.width,
        height: rect.height,
        centerX: rect.left + rect.width / 2 - containerRect.left,
        centerY: rect.top + rect.height / 2 - containerRect.top,
      };
    };

    // Main vertical path
    this.connect(getCoords, 'step1', 'step2', 'vertical');
    this.connect(getCoords, 'step2', 'step3', 'vertical');

    // Branching logic
    const decisionCoords = getCoords('step3');
    const branchACoords = getCoords('step4a');
    const branchBCoords = getCoords('step4b');

    if (decisionCoords && branchACoords && branchBCoords) {
      const midX = decisionCoords.right + 40;

      // 1. Horizontal line from decision right to the vertical line
      this.lines.push({
        x1: decisionCoords.right, y1: decisionCoords.centerY,
        x2: midX, y2: decisionCoords.centerY,
      });

      // 2. Vertical line connecting the two branches
      this.lines.push({
        x1: midX, y1: branchACoords.centerY,
        x2: midX, y2: branchBCoords.centerY,
      });

      // 3. Horizontal line from vertical line to branch A
      this.lines.push({
        x1: midX, y1: branchACoords.centerY,
        x2: branchACoords.left, y2: branchACoords.centerY,
      });

      // 4. Horizontal line from vertical line to branch B
      this.lines.push({
        x1: midX, y1: branchBCoords.centerY,
        x2: branchBCoords.left, y2: branchBCoords.centerY,
      });
    }

    // Vertical paths within branches
    this.connect(getCoords, 'step4a', 'step5a', 'vertical');
    this.connect(getCoords, 'step4b', 'step5b', 'vertical');
  }

  private connect(getCoords: (id: string) => any, startId: string, endId: string, type: 'horizontal' | 'vertical'): void {
    const start = getCoords(startId);
    const end = getCoords(endId);
    if (this.lines && start && end) {
        if (type === 'horizontal') {
            this.lines.push({ x1: start.right, y1: start.centerY, x2: end.left, y2: end.centerY });
        } else { // vertical
            this.lines.push({ x1: start.centerX, y1: start.bottom, x2: end.centerX, y2: end.top });
        }
    }
  }
}
