import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SpeechTranslationService, TranslationResult } from '../../services/speech-translation.service';
import { Subject, takeUntil } from 'rxjs';
import { HttpClientModule } from '@angular/common/http';

interface LanguageOption {
  code: string;
  name: string;
}

@Component({
  selector: 'app-real-time-speech-translator',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule],
  templateUrl: './real-time-speech-translator.component.html',
  styleUrls: ['./real-time-speech-translator.component.scss'],
  providers: [SpeechTranslationService]
})
export class RealTimeSpeechTranslatorComponent implements OnInit, OnDestroy {
  sourceLanguage = 'en';
  targetLanguage = 'es';
  isListening = false;
  connectionStatus = 'disconnected';
  originalText = '';
  translatedText = '';
  interimOriginalText = '';
  interimTranslatedText = '';
  errorMessage = '';
  fullOriginalText = '';
  fullTranslatedText = '';
  showFullText = false;

  private destroy$ = new Subject<void>();

  languageOptions: LanguageOption[] = [
    { code: 'en', name: 'English' },
    { code: 'es', name: 'Spanish' },
    { code: 'fr', name: 'French' },
    { code: 'de', name: 'German' },
    { code: 'it', name: 'Italian' },
    { code: 'ja', name: 'Japanese' },
    { code: 'ko', name: 'Korean' },
    { code: 'zh-Hans', name: 'Chinese (Simplified)' },
    { code: 'ar', name: 'Arabic' },
    { code: 'ru', name: 'Russian' }
  ];

  constructor(private speechService: SpeechTranslationService) {}

  ngOnInit(): void {
    this.initializeConnection();
    this.listenForTranslations();
    this.listenForInterimTranslations();
    this.listenForFullTranslation();
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
    this.speechService.disconnectSignalR();
  }

  private initializeConnection(): void {
    this.speechService.initializeConnection()
      .then(() => {
        console.log('Connected to translation service');
        this.errorMessage = '';
      })
      .catch(err => {
        console.error('Failed to connect to translation service', err);
        this.errorMessage = 'Failed to connect to the translation service. Please try again later.';
      });

    this.speechService.connectionStatus$
      .pipe(takeUntil(this.destroy$))
      .subscribe(status => {
        this.connectionStatus = status;
      });

    this.speechService.isListening$
      .pipe(takeUntil(this.destroy$))
      .subscribe(isListening => {
        this.isListening = isListening;
        if (!isListening) {
          // Clear interim text when we stop listening
          this.interimOriginalText = '';
          this.interimTranslatedText = '';
        }
      });
  }

  private listenForTranslations(): void {
    this.speechService.translationResult$
      .pipe(takeUntil(this.destroy$))
      .subscribe((result: TranslationResult | null) => {
        if (result) {
          this.originalText = result.originalText;
          this.translatedText = result.translatedText;
          
          // Clear interim text when we get final results
          this.interimOriginalText = '';
          this.interimTranslatedText = '';
        }
      });
  }
  
  private listenForInterimTranslations(): void {
    this.speechService.interimTranslation$
      .pipe(takeUntil(this.destroy$))
      .subscribe((result: TranslationResult | null) => {
        if (result) {
          this.interimOriginalText = result.originalText;
          this.interimTranslatedText = result.translatedText;
        }
      });
  }

  private listenForFullTranslation(): void {
    this.speechService.fullTranslationResult$
      .pipe(takeUntil(this.destroy$))
      .subscribe(result => {
        if (result) {
          this.fullOriginalText = result.originalText;
          this.fullTranslatedText = result.translatedText;
          this.showFullText = true;
        }
      });
  }

  startTranslation(): void {
    this.errorMessage = '';
    this.originalText = '';
    this.translatedText = '';
    this.interimOriginalText = '';
    this.interimTranslatedText = '';
    this.fullOriginalText = '';
    this.fullTranslatedText = '';
    this.showFullText = false;

    this.speechService.resetFullTranslation();

    this.speechService.startTranslation({
      sourceLanguage: this.sourceLanguage,
      targetLanguage: this.targetLanguage
    }).subscribe({
      next: () => console.log('Translation started'),
      error: err => {
        console.error('Error starting translation', err);
        this.errorMessage = 'Failed to start translation. Please try again.';
      }
    });
  }

  stopTranslation(): void {
    this.speechService.stopTranslation().subscribe({
      next: () => console.log('Translation stopped'),
      error: err => {
        console.error('Error stopping translation', err);
        this.errorMessage = 'Failed to stop translation. Please try again.';
      }
    });
  }

  toggleFullTextView(): void {
    this.showFullText = !this.showFullText;
  }

  getLanguageName(code: string): string {
    return this.languageOptions.find(lang => lang.code === code)?.name || code;
  }

  copyFullText(): void {
    const combinedText = `Original (${this.getLanguageName(this.sourceLanguage)}):\n${this.fullOriginalText}\n\nTranslation (${this.getLanguageName(this.targetLanguage)}):\n${this.fullTranslatedText}`;
    
    navigator.clipboard.writeText(combinedText)
      .then(() => {
        // Optional: Show a temporary success message
        const originalErrorMessage = this.errorMessage;
        this.errorMessage = 'Text copied to clipboard!';
        setTimeout(() => {
          this.errorMessage = originalErrorMessage;
        }, 2000);
      })
      .catch(err => {
        console.error('Failed to copy text: ', err);
      });
  }
}
