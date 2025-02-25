import { ComponentFixture, TestBed } from '@angular/core/testing';

import { GroupPostsListComponent } from './group-posts-list.component';

describe('GroupPostsListComponent', () => {
  let component: GroupPostsListComponent;
  let fixture: ComponentFixture<GroupPostsListComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [GroupPostsListComponent]
    });
    fixture = TestBed.createComponent(GroupPostsListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
