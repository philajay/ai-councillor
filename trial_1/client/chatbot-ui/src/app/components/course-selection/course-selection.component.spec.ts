import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CourseSelectionComponent } from './course-selection.component';

describe('CourseSelectionComponent', () => {
  let component: CourseSelectionComponent;
  let fixture: ComponentFixture<CourseSelectionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CourseSelectionComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(CourseSelectionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
