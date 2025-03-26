import { Component, OnInit } from '@angular/core';
import { FormGroup, FormBuilder, Validators, ReactiveFormsModule } from '@angular/forms';
import { AppService } from '../../app.service';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Router } from '@angular/router';
import { environment } from '../../shared/environments/environment';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { DeleteConfirmationDialogComponent } from './delete-confirmation-dialog.component';
import { supportedLanguages } from '../../shared/constant/data.constant';
import { NavbarMainComponent } from '../../layout/navbar-main/navbar-main.component';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';

interface EducationalConcern {
  label: string;
  severity: string;
}

@Component({
  selector: 'app-user-profile',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
    MatProgressSpinnerModule,
    MatDialogModule,
    NavbarMainComponent,
    MatSnackBarModule,
  ],
  templateUrl: './user-profile.component.html',
  styleUrls: ['./user-profile.component.scss'],
})
export class UserProfileComponent implements OnInit {
  /** Form and UI states */
  profileForm!: FormGroup;
  isLoading: boolean = true;
  isSubmitting: boolean = false;
  activeTab: string = 'basic';

  /** For the custom gender slider */
  genders: string[] = ['male', 'female', 'other'];
  genderIndex: number = 0;

  /** For profile image upload */
  selectedFile: File | null = null;
  selectedImageUrl: any = null;
  currentProfilePicture: any = '';

  /** For language preferences */
  preferredLanguage: string = 'en';
  translatedTexts: { [key: string]: string } = {};
  supportedLanguages = supportedLanguages;

  /** User Journey Data (loaded from backend) */
  studentGoals: string[] = [];
  interestedSubjects: string[] = [];
  mentalHealthConcerns: EducationalConcern[] = [];
  studyPlanExercises: string[] = [];
  studyPlanAssignments: string[] = [];
  studyPlanResources: string[] = [];
  
  /** Accordion state */
  isAccordionOpen = {
    exercises: false,
    assignments: false,
    resources: false
  };

  /** environment / backend */
  baseUrl: string = environment.baseUrl;
  backendUrl: string = environment.baseUrl;

  constructor(
    private fb: FormBuilder,
    private appService: AppService,
    private router: Router,
    private dialog: MatDialog,
    private snackBar: MatSnackBar,
  ) {}

  ngOnInit(): void {
    // Check authentication
    if (!this.appService.isAuthenticated()) {
      this.router.navigate(['/auth/sign-in'], {
        queryParams: { error: 'Please sign in to access your profile.' }
      });
      return;
    }

    // Initialize form
    this.profileForm = this.fb.group({
      username: [{ value: '', disabled: true }, [Validators.required, Validators.minLength(3), this.alphanumericValidator]],
      email: [{ value: '', disabled: true }, [Validators.required, Validators.email]],
      name: ['', [Validators.minLength(2)]],
      age: ['', [Validators.min(18), Validators.max(120)]],
      gender: [''],
      placeOfResidence: [''],
      fieldOfStudy: [''],
      preferredLanguage: ['en']
    });

    // Fetch user data from backend
    this.fetchUserProfile();

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

  /** When switching tabs, also re-check for new text that needs translation */
  setActiveTab(tab: string): void {
    this.activeTab = tab;
    
    // Let Angular render the tab; then do dynamic translation
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
      'My Profile',
      'Your Name',
      'N/A',
      'Name:',
      'Username:',
      'Email:',
      'Gender:',
      'Place of Residence:',
      'Your age',
      'Preferred Language',
      'Basic Info',
      'Academic',
      'Resources',
      'Wellbeing',
      'Save Profile',
      'Updating...',
      'Delete Account',
      'Processing...',
      'Add exercise...',
      'Add assignment...',
      'Add resource...',
      'Concern label...',
      'Add Concern',
      'Add a goal...',
      'Add a subject...',
      'Your field of study',
      'Field of Study:',
      'Academic Goals:',
      'Interested Subjects:',
      'Study Plan:',
      'Exercises',
      'Assignments',
      'Resources',
      'Educational Concerns:',
      'male',
      'female',
      'other',
      'low',
      'medium',
      'high',
      'Language:',
      // Add snackbar messages for translation
      'Profile updated successfully!',
      'Please correct the errors in the form.',
      'Failed to update profile.',
      'Your profile has been deleted successfully.',
      'An error occurred while deleting your profile.',
      'Failed to load profile. Please try again later.',
      'Close'
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
  //    (like tabs that appear after init)
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

  //=========================================
  // 3) Fetch Profile & Translate Backend Data
  //=========================================
  fetchUserProfile(): void {
    this.appService.getUserProfile().subscribe({
      next: (response) => {
        // Patch basic user form
        this.profileForm.patchValue({
          username: response.username || '',
          email: response.email || '',
          name: response.name || '',
          age: response.age || '',
          gender: response.gender || '',
          placeOfResidence: response.placeOfResidence || '',
          fieldOfStudy: response.fieldOfStudy || '',
          preferredLanguage: response.preferredLanguage || 'en'
        });
  
        // Update gender slider
        const genderFromBackend = response.gender || 'male';
        const idx = this.genders.indexOf(genderFromBackend);
        this.genderIndex = idx >= 0 ? idx : 0;
  
        // Profile pic
        if (response.profile_picture) {
          this.currentProfilePicture = response.profile_picture.startsWith('http')
            ? response.profile_picture
            : `${this.backendUrl}${response.profile_picture}`;
        } else {
          this.currentProfilePicture = '/assets/img/user_avtar.jpg';
        }
  
        // Load user journey data if available
        if (response.user_journey) {
          try {
            // Student goals
            this.studentGoals = this.parseStringOrArray(response.user_journey.student_goals);
            // Interested subjects
            this.interestedSubjects = this.parseStringOrArray(response.user_journey.interested_subjects);
            // Mental health concerns
            const concerns = this.parseStringOrArray(response.user_journey.mental_health_concerns);
            // The “concerns” array is an array of objects, so parse carefully
            if (Array.isArray(concerns)) {
              this.mentalHealthConcerns = concerns as EducationalConcern[];
            }

            // Study plan
            if (response.user_journey.Study_plan) {
              const studyPlan = typeof response.user_journey.Study_plan === 'string' 
                ? JSON.parse(response.user_journey.Study_plan)
                : response.user_journey.Study_plan;

              this.studyPlanExercises = studyPlan.exercise || [];
              this.studyPlanAssignments = [
                ...(studyPlan.assign_assignments || []),
                ...(studyPlan.submit_assignments || [])
              ];
              this.studyPlanResources = studyPlan.share_resources || [];
            }
          } catch (error) {
            console.error('Error parsing user journey data:', error);
          }
        }

        this.isLoading = false;

        // -- IMPORTANT: Now we translate the text from backend arrays
        if (this.preferredLanguage !== 'en') {
          this.translateJourneyData(this.preferredLanguage);
        }
      },
      error: (error) => {
        console.error('Error fetching user profile:', error);
        this.snackBar.open(
          error.error?.error || this.translatedTexts['Failed to load profile. Please try again later.'] || 'Failed to load profile. Please try again later.',
          this.translatedTexts['Close'] || 'Close',
          { duration: 3000, horizontalPosition: 'center' }
        );
        this.isLoading = false;
      }
    });
  }

  /**
   * Safely parse a JSON string or handle array
   */
  private parseStringOrArray(value: any): any[] {
    if (typeof value === 'string') {
      try {
        return JSON.parse(value);
      } catch (err) {
        return [];
      }
    } else if (Array.isArray(value)) {
      return value;
    } else {
      return [];
    }
  }

  /**
   * Translate user journey data from backend
   * (studentGoals, interestedSubjects, study plan items, etc.)
   */
  private translateJourneyData(language: string): void {
    // 1) Gather all strings to translate from the arrays
    // (For mentalHealthConcerns, we only have 'label' that needs translation)
    const journeyTexts = [
      ...this.studentGoals,
      ...this.interestedSubjects,
      ...this.studyPlanExercises,
      ...this.studyPlanAssignments,
      ...this.studyPlanResources,
      ...this.mentalHealthConcerns.map(c => c.label || '')
    ].filter(t => t && t.trim() !== '');

    // If empty or user wants en, skip
    if (!journeyTexts.length || language === 'en') {
      // Still do a dynamic content pass (in case the DOM has new data-translate elements).
      setTimeout(() => this.translateDynamicContent(), 300);
      return;
    }

    this.appService.translateTexts(journeyTexts, language).subscribe({
      next: (response) => {
        const translations = response.translations;
        let idx = 0;

        // Overwrite each array with translations in the same order
        this.studentGoals = this.studentGoals.map(g => {
          if (!g.trim()) { return g; }
          const result = translations[idx];
          idx++;
          return result;
        });
        this.interestedSubjects = this.interestedSubjects.map(s => {
          if (!s.trim()) { return s; }
          const result = translations[idx];
          idx++;
          return result;
        });
        this.studyPlanExercises = this.studyPlanExercises.map(e => {
          if (!e.trim()) { return e; }
          const result = translations[idx];
          idx++;
          return result;
        });
        this.studyPlanAssignments = this.studyPlanAssignments.map(a => {
          if (!a.trim()) { return a; }
          const result = translations[idx];
          idx++;
          return result;
        });
        this.studyPlanResources = this.studyPlanResources.map(r => {
          if (!r.trim()) { return r; }
          const result = translations[idx];
          idx++;
          return result;
        });
        this.mentalHealthConcerns = this.mentalHealthConcerns.map(c => {
          if (!c.label.trim()) { return c; }
          const result = translations[idx];
          idx++;
          return { ...c, label: result };
        });

        // Now that arrays have been replaced with translated strings, 
        // let's do a dynamic content translation pass for any new DOM text
        setTimeout(() => this.translateDynamicContent(), 300);
      },
      error: (err) => {
        console.error('Error translating backend data:', err);
      }
    });
  }

  /** Gender slider control */
  changeGender(direction: number): void {
    this.genderIndex += direction;
    if (this.genderIndex < 0) {
      this.genderIndex = this.genders.length - 1;
    } else if (this.genderIndex >= this.genders.length) {
      this.genderIndex = 0;
    }
    const currentGender = this.genders[this.genderIndex];
    this.profileForm.patchValue({ gender: currentGender });
  }

  /** Upload avatar */
  onFileSelected(event: Event): void {
    const input: any = event.target;
    if (input.files && input.files.length > 0) {
      const file: File = input.files[0];
      const reader = new FileReader();
      reader.onload = (e) => {
        this.selectedImageUrl = e.target?.result;
        this.currentProfilePicture = e.target?.result;
      };
      reader.readAsDataURL(file);
      this.selectedFile = file;
    }
  }

  /** Submit the profile form */
  onSubmit(): void {
    if (this.profileForm.invalid) {
      this.snackBar.open(
        this.translatedTexts['Please correct the errors in the form.'] || 'Please correct the errors in the form.',
        this.translatedTexts['Close'] || 'Close',
        { duration: 3000, horizontalPosition: 'center' }
      );
      return;
    }

    this.isSubmitting = true;
    
    const formData = new FormData();
    const updatedData = this.profileForm.value;

    // Append user fields
    for (const key in updatedData) {
      if (updatedData.hasOwnProperty(key)) {
        formData.append(key, updatedData[key]);
      }
    }

    // Append user journey fields
    formData.append('student_goals', JSON.stringify(this.studentGoals));
    formData.append('interested_subjects', JSON.stringify(this.interestedSubjects));
    formData.append('mental_health_concerns', JSON.stringify(this.mentalHealthConcerns));
    
    // Build study plan object
    const studyPlan = {
      exercise: this.studyPlanExercises,
      submit_assignments: this.studyPlanAssignments.slice(0, Math.floor(this.studyPlanAssignments.length / 2)),
      assign_assignments: this.studyPlanAssignments.slice(Math.floor(this.studyPlanAssignments.length / 2)),
      share_resources: this.studyPlanResources
    };
    formData.append('Study_plan', JSON.stringify(studyPlan));

    // Append profile picture if selected
    if (this.selectedFile) {
      formData.append('profile_picture', this.selectedFile);
    }

    this.appService.updateUserProfile(formData).subscribe({
      next: (response) => {
        this.snackBar.open(
          this.translatedTexts['Profile updated successfully!'] || 'Profile updated successfully!',
          this.translatedTexts['Close'] || 'Close',
          { duration: 3000, horizontalPosition: 'center' }
        );

        // If the user changed language, re-translate
        const newPreferredLanguage = this.profileForm.get('preferredLanguage')?.value;
        if (newPreferredLanguage && newPreferredLanguage !== this.preferredLanguage) {
          this.preferredLanguage = newPreferredLanguage;
          localStorage.setItem('preferredLanguage', newPreferredLanguage);
          // Re-translate the content in the new language
          this.translateContent(newPreferredLanguage);
          // Also re-translate any backend data arrays if necessary
          this.translateJourneyData(newPreferredLanguage);
        }

        this.isSubmitting = false;
      },
      error: (error) => {
        console.error('Error updating profile:', error);
        this.snackBar.open(
          error.error?.error || this.translatedTexts['Failed to update profile.'] || 'Failed to update profile.',
          this.translatedTexts['Close'] || 'Close',
          { duration: 3000, horizontalPosition: 'center' }
        );
        this.isSubmitting = false;
      }
    });
  }

  /** Click avatar to choose file */
  triggerFileInput(fileInput: HTMLInputElement): void {
    fileInput.click();
  }

  /** Show delete confirmation dialog */
  openDeleteConfirmationDialog(): void {
    // Add these dialog text strings to the translation service when fetching translations
    const dialogTexts = [
      'Confirm Deletion',
      'Are you sure you want to delete your profile? This action cannot be undone.',
      'Cancel',
      'Delete'
    ];
    
    // If not English, translate the dialog texts first
    if (this.preferredLanguage !== 'en') {
      this.appService.translateTexts(dialogTexts, this.preferredLanguage).subscribe({
        next: (response) => {
          const translations = response.translations;
          
          // Store translations in our dictionary
          dialogTexts.forEach((text, idx) => {
            this.translatedTexts[text] = translations[idx];
          });
          
          // Now open the dialog with the translated texts
          this.openConfirmDialog();
        },
        error: (err) => {
          console.error('Translation error for dialog:', err);
          // Fall back to opening dialog without translations
          this.openConfirmDialog();
        }
      });
    } else {
      // Just open the dialog in English
      this.openConfirmDialog();
    }
  }

  /** Helper to open the actual dialog */
  private openConfirmDialog(): void {
    const dialogRef = this.dialog.open(DeleteConfirmationDialogComponent, {
      data: { translations: this.translatedTexts }
    });
    
    dialogRef.afterClosed().subscribe(result => {
      if (result === true) {
        this.deleteProfile();
      }
    });
  }

  /** Delete user profile */
  deleteProfile(): void {
    this.isSubmitting = true;
    this.appService.deleteUserProfile().subscribe(
      response => {
        this.isSubmitting = false;
        this.snackBar.open(
          this.translatedTexts['Your profile has been deleted successfully.'] || 'Your profile has been deleted successfully.',
          this.translatedTexts['Close'] || 'Close',
          { duration: 3000, horizontalPosition: 'center' }
        );
        this.appService.signOut();
        this.router.navigate(['/auth/sign-up']);
      },
      error => {
        this.isSubmitting = false;
        this.snackBar.open(
          this.translatedTexts['An error occurred while deleting your profile.'] || 'An error occurred while deleting your profile.',
          this.translatedTexts['Close'] || 'Close',
          { duration: 3000, horizontalPosition: 'center' }
        );
      }
    );
  }

  /** Accordion controls (Resources tab) */
  toggleAccordion(section: string): void {
    this.isAccordionOpen[section as keyof typeof this.isAccordionOpen] = 
      !this.isAccordionOpen[section as keyof typeof this.isAccordionOpen];
    
    // If we opened the accordion, re-check translations
    if (this.isAccordionOpen[section as keyof typeof this.isAccordionOpen] && this.preferredLanguage !== 'en') {
      setTimeout(() => this.translateDynamicContent(), 300);
    }
  }

  /**
   * Student goals
   */
  addStudentGoal(goal: string): void {
    if (goal && goal.trim() !== '' && !this.studentGoals.includes(goal)) {
      this.studentGoals.push(goal.trim());
    }
  }
  removeStudentGoal(index: number): void {
    this.studentGoals.splice(index, 1);
  }

  /**
   * Interested subjects
   */
  addInterestedSubject(subject: string): void {
    if (subject && subject.trim() !== '' && !this.interestedSubjects.includes(subject)) {
      this.interestedSubjects.push(subject.trim());
    }
  }
  removeInterestedSubject(index: number): void {
    this.interestedSubjects.splice(index, 1);
  }

  /**
   * Study plan
   */
  addStudyPlanExercise(exercise: string): void {
    if (exercise && exercise.trim() !== '') {
      this.studyPlanExercises.push(exercise.trim());
    }
  }
  removeStudyPlanExercise(index: number): void {
    this.studyPlanExercises.splice(index, 1);
  }

  addStudyPlanAssignment(assignment: string): void {
    if (assignment && assignment.trim() !== '') {
      this.studyPlanAssignments.push(assignment.trim());
    }
  }
  removeStudyPlanAssignment(index: number): void {
    this.studyPlanAssignments.splice(index, 1);
  }

  addStudyPlanResource(resource: string): void {
    if (resource && resource.trim() !== '') {
      this.studyPlanResources.push(resource.trim());
    }
  }
  removeStudyPlanResource(index: number): void {
    this.studyPlanResources.splice(index, 1);
  }

  /**
   * Mental health concerns
   */
  addConcern(label: string, severity: string): void {
    if (label && label.trim() !== '') {
      this.mentalHealthConcerns.push({
        label: label.trim(),
        severity: severity || 'medium'
      });
    }
  }
  removeConcern(index: number): void {
    this.mentalHealthConcerns.splice(index, 1);
  }

  /**
   * Custom validator to ensure username is alphanumeric
   */
  alphanumericValidator(control: any) {
    const value = control.value;
    if (value && !/^[a-zA-Z0-9]+$/.test(value)) {
      return { alphanumeric: true };
    }
    return null;
  }
}
