import { ComponentFixture, TestBed } from '@angular/core/testing';

import { RealTimeSpeechTranslatorComponent } from './real-time-speech-translator.component';

describe('RealTimeSpeechTranslatorComponent', () => {
  let component: RealTimeSpeechTranslatorComponent;
  let fixture: ComponentFixture<RealTimeSpeechTranslatorComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [RealTimeSpeechTranslatorComponent]
    });
    fixture = TestBed.createComponent(RealTimeSpeechTranslatorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
