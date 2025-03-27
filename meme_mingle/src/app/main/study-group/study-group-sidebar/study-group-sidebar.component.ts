// src/app/main/study-group/study-group-sidebar/study-group-sidebar.component.ts
import { Component, OnInit, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AppService } from 'src/app/app.service';
import { RouterModule, Router } from '@angular/router';
import { SidebarService } from 'src/app/shared/service/study-group-sidebar.service';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-study-group-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './study-group-sidebar.component.html',
  styleUrls: ['./study-group-sidebar.component.scss']
})
export class StudyGroupSidebarComponent implements OnInit, AfterViewInit {
  groups: any[] = [];
  filteredGroups: any[] = []; // Store filtered groups
  searchTerm: string = ''; // For search functionality
  loading: boolean = false;
  errorMessage: string = '';
  sidebarVisible: boolean = true; // Tracks sidebar visibility
  toggleIcon: string = '<';
  userId: string = '';
  selectedGroupId: string = '';
  
  // Translation related properties
  preferredLanguage: string = 'en';
  translatedTexts: { [key: string]: string } = {};

  constructor(private appService: AppService, private router: Router, private sidebarService: SidebarService) {}

  ngOnInit(): void {
    this.loadGroups();
    this.userId = localStorage.getItem('user_id') || '';
    this.sidebarService.getSidebarState().subscribe((visible: boolean) => {
      this.sidebarVisible = visible;
    });
    
    // Load from localStorage if user has previously chosen a language
    this.preferredLanguage = localStorage.getItem('preferredLanguage') || 'en';

    // If user's language is not English, do an initial pass of translation
    if (this.preferredLanguage !== 'en') {
      this.translateContent(this.preferredLanguage);
    }
  }

  // Once view is initialized, handle any leftover dynamic text
  ngAfterViewInit(): void {
    setTimeout(() => {
      if (this.preferredLanguage !== 'en') {
        this.translateDynamicContent();
      }
    }, 300);
  }

  //=========================================
  // 1) Translate All Static Content
  //=========================================
  private translateContent(targetLanguage: string) {
    // 1) Grab the text from all elements marked with data-translate
    const elementsToTranslate = document.querySelectorAll('[data-translate]');
    const textsInDom = Array.from(elementsToTranslate).map(
      (el) => el.textContent?.trim() || ''
    );

    // 2) Include additional strings you might need from code
    const additionalTexts = [
      'Study Groups',
      'Toggle Sidebar',
      'Create New Group',
      'Search groups...',
      'Loading groups...',
      'No study groups found. Create a new group or join existing ones!',
      'Create Group',
      'Join',
      'Group Image',
      'Error retrieving groups',
      'Group ID not found.',
      'Error joining group.',
      'You have not joined this group yet.'
    ];

    // Combine them into a unique set
    const combinedSet = new Set([...textsInDom, ...additionalTexts].filter(Boolean));
    const allTextsToTranslate = Array.from(combinedSet);

    // If target language is English or nothing to translate, skip
    if (!allTextsToTranslate.length || targetLanguage === 'en') {
      return;
    }

    // 3) Call the translation service
    this.appService.translateTexts(allTextsToTranslate, targetLanguage).subscribe({
      next: (response) => {
        const translations = response.translations;
        // Store them in our dictionary
        allTextsToTranslate.forEach((original, idx) => {
          this.translatedTexts[original] = translations[idx];
        });
        // Update the DOM
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

  //=========================================
  // 2) Translate Any New DOM Elements
  //    (like dynamic content that appears after init)
  //=========================================
  private translateDynamicContent(): void {
    if (this.preferredLanguage === 'en') return;
    
    const elementsToTranslate = document.querySelectorAll('[data-translate]');
    const textsInDom = Array.from(elementsToTranslate).map(
      (el) => el.textContent?.trim() || ''
    );

    // Filter out any you already have
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

    // call translation service for the new strings
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

  // Filter groups based on search term
  filterGroups(): void {
    if (!this.searchTerm.trim()) {
      this.filteredGroups = [...this.groups];
      return;
    }
    
    const term = this.searchTerm.toLowerCase().trim();
    this.filteredGroups = this.groups.filter(group => 
      group.name.toLowerCase().includes(term) || 
      (group.description && group.description.toLowerCase().includes(term))
    );
  }

  loadGroups(): void {
    this.loading = true;
    this.appService.getGroups().subscribe({
      next: (response: { data: any[] }) => {
        // Assume response.data contains the list of groups
        this.groups = response.data;
        this.filteredGroups = [...this.groups]; // Initialize filtered groups
        console.log('Groups:', this.groups);
        this.loading = false;
  
        // Translate group names and descriptions if not in English
        if (this.preferredLanguage !== 'en') {
          this.translateGroupContent();
        }
  
        // Translate dynamic content after loading groups
        if (this.preferredLanguage !== 'en') {
          setTimeout(() => this.translateDynamicContent(), 100);
        }
      },
      error: (error: any) => {
        this.errorMessage = error.error?.error || 
          (this.translatedTexts['Error retrieving groups'] || 'Error retrieving groups');
        this.loading = false;
      }
    });
  }
  
  // Add this new method to translate group content from backend
  translateGroupContent(): void {
    if (!this.groups || this.groups.length === 0) return;
    
    // Collect all the text that needs translation
    const textsToTranslate: string[] = [];
    const groupsMap: Map<number, {nameIndex: number, descIndex: number}> = new Map();
    
    this.groups.forEach((group, i) => {
      if (group.name) {
        groupsMap.set(i, {
          nameIndex: textsToTranslate.length,
          descIndex: group.description ? textsToTranslate.length + 1 : -1
        });
        textsToTranslate.push(group.name);
        if (group.description) {
          textsToTranslate.push(group.description);
        }
      }
    });
    
    if (textsToTranslate.length === 0) return;
    
    // Call translation service
    this.appService.translateTexts(textsToTranslate, this.preferredLanguage).subscribe({
      next: (response) => {
        const translations = response.translations;
        
        // Update each group with translated content
        this.groups.forEach((group, i) => {
          const indices = groupsMap.get(i);
          if (indices) {
            // Store original text for reference
            const originalName = group.name;
            const originalDesc = group.description;
            
            // Update with translated text
            group.name = translations[indices.nameIndex];
            if (indices.descIndex !== -1) {
              group.description = translations[indices.descIndex];
            }
            
            // Store originals in translatedTexts map for reference
            this.translatedTexts[originalName] = group.name;
            if (originalDesc) {
              this.translatedTexts[originalDesc] = group.description;
            }
          }
        });
        
        // Update filtered groups with translated content
        this.filteredGroups = [...this.groups];
      },
      error: (err) => {
        console.error('Error translating group content:', err);
      }
    });
  }

  joinGroup(group: any): void {
    console.log('Group data:', group);
    if (!group?.id) {
      this.errorMessage = this.translatedTexts['Group ID not found.'] || 'Group ID not found.';
      return;
    }
    if (!this.userId) {
      this.router.navigate(['/auth/sign-in'], { queryParams: { returnUrl: this.router.url } });
      return;
    }
    this.loading = true;
    const payload = {
      group_id: group.id,
      user_id: this.userId
    };
    this.appService.joinGroup(payload).subscribe({
      next: (response) => {
        console.log('Joined group successfully:', response);
        if (!group.members) {
          group.members = [];
        }
        group.members.push(this.userId);
        this.loading = false;
      },
      error: (error) => {
        this.errorMessage = error.error?.error || 
          (this.translatedTexts['Error joining group.'] || 'Error joining group.');
        this.loading = false;
      }
    });
  }

  // Toggles the sidebar visibility
  toggleSidebar(): void {
    this.sidebarVisible = !this.sidebarVisible;
    this.toggleIcon = this.sidebarVisible ? '<' : '>';
    this.sidebarService.toggleSidebar(); // Notify service about the change
  }

  openGroupPosts(group: any): void {
    if (group.members?.includes(this.userId)) {
      this.selectedGroupId = group.id;
      this.router.navigate(['/main/study-group/group-posts', group.id]);
    } else {
      console.log(this.translatedTexts['You have not joined this group yet.'] || 'You have not joined this group yet.');
    }
  }
}
