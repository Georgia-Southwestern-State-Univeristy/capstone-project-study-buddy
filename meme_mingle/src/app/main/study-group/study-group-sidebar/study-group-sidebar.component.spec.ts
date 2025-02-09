import { ComponentFixture, TestBed } from '@angular/core/testing';

import { StudyGroupSidebarComponent } from './study-group-sidebar.component';

describe('StudyGroupSidebarComponent', () => {
  let component: StudyGroupSidebarComponent;
  let fixture: ComponentFixture<StudyGroupSidebarComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [StudyGroupSidebarComponent]
    });
    fixture = TestBed.createComponent(StudyGroupSidebarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
