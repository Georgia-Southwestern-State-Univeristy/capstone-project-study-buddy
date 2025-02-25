import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CreateGroupPostComponent } from './create-group-post.component';

describe('CreateGroupPostComponent', () => {
  let component: CreateGroupPostComponent;
  let fixture: ComponentFixture<CreateGroupPostComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [CreateGroupPostComponent]
    });
    fixture = TestBed.createComponent(CreateGroupPostComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
