import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SuggestionChipsComponent } from './suggestion-chips.component';

describe('SuggestionChipsComponent', () => {
  let component: SuggestionChipsComponent;
  let fixture: ComponentFixture<SuggestionChipsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SuggestionChipsComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(SuggestionChipsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
