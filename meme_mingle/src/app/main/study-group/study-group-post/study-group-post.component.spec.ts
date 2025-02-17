import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StudyGroupPostComponent } from './study-group-post.component';

describe('StudyGroupPostComponent', () => {
  let component: StudyGroupPostComponent;
  let fixture: ComponentFixture<StudyGroupPostComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [StudyGroupPostComponent]
    });
    fixture = TestBed.createComponent(StudyGroupPostComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
