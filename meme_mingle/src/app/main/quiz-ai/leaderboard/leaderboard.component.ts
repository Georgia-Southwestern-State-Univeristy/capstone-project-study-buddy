import { Component, OnInit, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AppService } from '../../../app.service';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-leaderboard',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule],
  templateUrl: './leaderboard.component.html',
  styleUrls: ['./leaderboard.component.scss']
})
export class LeaderboardComponent implements OnInit {
  leaderboardData: any[] = [];
  @Input() translatedTexts: { [key: string]: string } = {};
  preferredLanguage: string = 'en';

  constructor(private appService: AppService) {}

  ngOnInit() {
    this.preferredLanguage = localStorage.getItem('preferredLanguage') || 'en';
    this.getLeaderboard();
    
    if (this.preferredLanguage !== 'en') {
      this.translateContent(this.preferredLanguage);
    }
  }

  getLeaderboard() {
    this.appService.getLeaderboard().subscribe({
      next: (data) => {
        this.leaderboardData = data.leaderboard || [];
      },
      error: (err) => {
        console.error('Error fetching leaderboard:', err);
      },
    });
  }

  // Add translation method
  translateContent(targetLanguage: string) {
    // Define texts that need translation
    const textsToTranslate = [
      'Leaderboard',
      'Rank',
      'User',
      'Quizzes',
      'Score',
      'No quiz results yet. Be the first to take a quiz!'
    ];

    this.appService.translateTexts(textsToTranslate, targetLanguage)
      .subscribe({
        next: (response) => {
          const translations = response.translations;
          
          // Update translatedTexts object with translations
          textsToTranslate.forEach((text, index) => {
            this.translatedTexts[text] = translations[index];
          });
          
          // After getting translations, update the DOM elements with data-translate attribute
          setTimeout(() => {
            this.updateTranslatedElements();
          }, 0);
        },
        error: (error) => {
          console.error('Error translating texts:', error);
        }
      });
  }

  // Method to update DOM elements with translations
  updateTranslatedElements() {
    const elementsToTranslate = document.querySelectorAll('[data-translate]');
    
    elementsToTranslate.forEach((element) => {
      const originalText = element.textContent?.trim() || '';
      if (this.translatedTexts[originalText] && !(element.tagName.startsWith('MAT-'))) {
        element.textContent = this.translatedTexts[originalText];
      }
    });
  }
}