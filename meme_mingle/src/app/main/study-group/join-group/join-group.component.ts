// src/app/main/study-group/join-group/join-group.component.ts
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AppService } from 'src/app/app.service';

@Component({
  selector: 'app-join-group',
  templateUrl: './join-group.component.html',
  styleUrls: ['./join-group.component.scss'],
  standalone: true,
  imports: [CommonModule]
})
export class JoinGroupComponent implements OnInit {
  groupId: string = '';
  message: string = '';
  errorMessage: string = '';
  loading: boolean = false;
  
  // Add translation related properties
  preferredLanguage: string = 'en';
  translatedTexts: { [key: string]: string } = {};

  constructor(
    private route: ActivatedRoute,
    private appService: AppService,
    private router: Router
  ) {}

  ngOnInit(): void {
    // Load preferred language from localStorage
    this.preferredLanguage = localStorage.getItem('preferredLanguage') || 'en';

    // Retrieve the group_id query parameter
    this.route.queryParams.subscribe(params => {
      this.groupId = params['group_id'];
      if (this.groupId) {
        this.joinGroup();
      } else {
        this.errorMessage = 'Invalid group link. Group ID not found.';
        // Translate error message if not in English
        if (this.preferredLanguage !== 'en') {
          this.translateText([this.errorMessage]);
        }
      }
    });

    // If user's language is not English, do an initial translation
    if (this.preferredLanguage !== 'en') {
      this.translateContent(this.preferredLanguage);
    }
  }

  ngAfterViewInit(): void {
    setTimeout(() => {
      if (this.preferredLanguage !== 'en') {
        this.translateDynamicContent();
      }
    }, 300);
  }

  /**
   * Translate static content in the component
   */
  private translateContent(targetLanguage: string) {
    // Skip if English is selected
    if (targetLanguage === 'en') return;

    // 1) Grab text from elements with data-translate attribute
    const elementsToTranslate = document.querySelectorAll('[data-translate]');
    const textsInDom = Array.from(elementsToTranslate).map(
      (el) => el.textContent?.trim() || ''
    );

    // 2) Include additional text strings
    const additionalTexts = [
      'Join Group',
      'Joining group...',
      'Invalid group link. Group ID not found.',
      'You have successfully joined the group!',
      'An error occurred while joining the group.'
    ];

    // 3) Combine unique text strings
    const combinedSet = new Set([...textsInDom, ...additionalTexts].filter(Boolean));
    const allTextsToTranslate = Array.from(combinedSet);

    if (!allTextsToTranslate.length) {
      return;
    }

    // 4) Call translation service
    this.appService.translateTexts(allTextsToTranslate, targetLanguage).subscribe({
      next: (response) => {
        const translations = response.translations;
        // Store translations in our dictionary
        allTextsToTranslate.forEach((original, idx) => {
          this.translatedTexts[original] = translations[idx];
        });
        // Update DOM elements
        elementsToTranslate.forEach((element) => {
          const originalText = element.textContent?.trim() || '';
          if (this.translatedTexts[originalText]) {
            element.textContent = this.translatedTexts[originalText];
          }
        });
      },
      error: (err) => {
        console.error('Translation error:', err);
      }
    });
  }

  /**
   * Translate dynamic content that may appear after init
   */
  private translateDynamicContent(): void {
    if (this.preferredLanguage === 'en') return;
    
    const elementsToTranslate = document.querySelectorAll('[data-translate]');
    const textsInDom = Array.from(elementsToTranslate).map(
      (el) => el.textContent?.trim() || ''
    );

    // Filter out any already translated text
    const notYetTranslated = textsInDom.filter(t => !this.translatedTexts[t] && t !== '');

    if (!notYetTranslated.length) {
      // everything is either translated or empty
      // just reassign to be safe
      elementsToTranslate.forEach((element) => {
        const text = element.textContent?.trim() || '';
        if (this.translatedTexts[text]) {
          element.textContent = this.translatedTexts[text];
        }
      });
      return;
    }

    // call translation service for new strings
    this.appService.translateTexts(notYetTranslated, this.preferredLanguage)
      .subscribe({
        next: (response) => {
          const translations = response.translations;
          notYetTranslated.forEach((original, i) => {
            this.translatedTexts[original] = translations[i];
          });
          // update the DOM
          elementsToTranslate.forEach((element) => {
            const text = element.textContent?.trim() || '';
            if (this.translatedTexts[text]) {
              element.textContent = this.translatedTexts[text];
            }
          });
        },
        error: (err) => console.error('Error translating dynamic content:', err)
      });
  }

  /**
   * Translate specific text strings
   */
  private translateText(texts: string[]): void {
    if (this.preferredLanguage === 'en' || !texts.length) return;
    
    this.appService.translateTexts(texts, this.preferredLanguage).subscribe({
      next: (response) => {
        const translations = response.translations;
        texts.forEach((original, idx) => {
          this.translatedTexts[original] = translations[idx];
        });
        
        // If this was an error message, update it
        if (this.errorMessage && this.translatedTexts[this.errorMessage]) {
          this.errorMessage = this.translatedTexts[this.errorMessage];
        }
        
        // If this was a success message, update it
        if (this.message && this.translatedTexts[this.message]) {
          this.message = this.translatedTexts[this.message];
        }
      },
      error: (err) => {
        console.error('Error translating text:', err);
      }
    });
  }

  joinGroup(): void {
    // Retrieve the current user's ID from localStorage
    const userId = localStorage.getItem('user_id');
    if (!userId) {
      // If the user is not authenticated, redirect them to the sign-in page.
      this.router.navigate(['/auth/sign-in'], { queryParams: { returnUrl: this.router.url } });
      return;
    }

    this.loading = true;
    const payload = {
      group_id: this.groupId,
      user_id: userId
    };

    this.appService.joinGroup(payload).subscribe({
      next: (response) => {
        this.message = response.message || 'You have successfully joined the group!';
        this.loading = false;
        
        // Translate success message if not in English
        if (this.preferredLanguage !== 'en') {
          this.translateText([this.message]);
        }
      },
      error: (error) => {
        this.errorMessage = error.error?.error || 'An error occurred while joining the group.';
        this.loading = false;
        
        // Translate error message if not in English
        if (this.preferredLanguage !== 'en') {
          this.translateText([this.errorMessage]);
        }
      }
    });
  }
}
