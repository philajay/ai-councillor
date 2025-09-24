import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CourseChipsComponent } from './course-chips.component';

describe('CourseChipsComponent', () => {
  let component: CourseChipsComponent;
  let fixture: ComponentFixture<CourseChipsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CourseChipsComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(CourseChipsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
