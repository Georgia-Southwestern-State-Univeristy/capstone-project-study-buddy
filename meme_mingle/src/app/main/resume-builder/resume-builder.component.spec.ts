import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ResumeBuilderComponent } from './resume-builder.component';

describe('ResumeBuilderComponent', () => {
  let component: ResumeBuilderComponent;
  let fixture: ComponentFixture<ResumeBuilderComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [ResumeBuilderComponent]
    });
    fixture = TestBed.createComponent(ResumeBuilderComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
