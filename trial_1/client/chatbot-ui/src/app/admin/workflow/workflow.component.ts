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
    this.connect(getCoords, 'step3', 'step4', 'vertical');

    // Branching logic
    const decisionCoords = getCoords('step4');
    const branchACoords = getCoords('step5a');
    const branchBCoords = getCoords('step5b');

    if (decisionCoords && branchACoords && branchBCoords) {
      const midY = decisionCoords.bottom + 40;

      // 1. Vertical line from decision down to the horizontal line level
      this.lines.push({
        x1: decisionCoords.centerX, y1: decisionCoords.bottom,
        x2: decisionCoords.centerX, y2: midY,
      });

      // 2. Horizontal line from center to branch A
      this.lines.push({
        x1: decisionCoords.centerX, y1: midY,
        x2: branchACoords.centerX, y2: midY,
      });

      // 3. Horizontal line from center to branch B
      this.lines.push({
        x1: decisionCoords.centerX, y1: midY,
        x2: branchBCoords.centerX, y2: midY,
      });

      // 4. Vertical line from horizontal line down to branch A
      this.lines.push({
        x1: branchACoords.centerX, y1: midY,
        x2: branchACoords.centerX, y2: branchACoords.top,
      });

      // 5. Vertical line from horizontal line down to branch B
      this.lines.push({
        x1: branchBCoords.centerX, y1: midY,
        x2: branchBCoords.centerX, y2: branchBCoords.top,
      });
    }

    // Vertical paths within branches
    this.connect(getCoords, 'step5a', 'step6a', 'vertical');
    this.connect(getCoords, 'step5b', 'step6b', 'vertical');
  }

  private connect(getCoords: (id: string) => any, startId: string, endId: string, type: 'horizontal' | 'vertical'): void {
    const start = getCoords(startId);
    const end = getCoords(endId);
    if (start && end) {
        if (type === 'horizontal') {
            this.lines.push({ x1: start.right, y1: start.centerY, x2: end.left, y2: end.centerY });
        } else { // vertical
            this.lines.push({ x1: start.centerX, y1: start.bottom, x2: end.centerX, y2: end.top });
        }
    }
  }
}
