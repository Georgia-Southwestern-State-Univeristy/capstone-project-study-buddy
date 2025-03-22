
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

  /** User Journey Data */
  studentGoals: string[] = [];
  interestedSubjects: string[] = [];
  mentalHealthConcerns: EducationalConcern[] = [];
  
  /** Study Plan Data */
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

    this.fetchUserProfile();

    this.preferredLanguage = localStorage.getItem('preferredLanguage') || 'en';
    if (this.preferredLanguage !== 'en') {
      this.translateContent(this.preferredLanguage);
    }
  }

  /**
   * Toggle accordion sections
   */
  toggleAccordion(section: string): void {
    this.isAccordionOpen[section as keyof typeof this.isAccordionOpen] = 
      !this.isAccordionOpen[section as keyof typeof this.isAccordionOpen];
  }

  /**
   * Student goals management
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
   * Interested subjects management
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
   * Study plan management
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
   * Mental health concerns management
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
   * Translate content to the target language
   */
  private translateContent(targetLanguage: string) {
    // Existing translation code...
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

  /**
   * Fetch the user profile from the backend
   */
  fetchUserProfile(): void {
    this.appService.getUserProfile().subscribe({
      next: (response) => {
        console.log('User profile fetched successfully:', response);
        
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
  
        // Handle profile picture
        if (response.profile_picture) {
          this.currentProfilePicture = response.profile_picture.startsWith('http')
            ? response.profile_picture
            : `${this.backendUrl}${response.profile_picture}`;
        } else {
          this.currentProfilePicture = '/assets/img/user_avtar.jpg';
        }
  
        // Load user journey data if available
        if (response.user_journey) {
          // Parse JSON strings for arrays if needed
          try {
            // Student goals
            this.studentGoals = typeof response.user_journey.student_goals === 'string'
              ? JSON.parse(response.user_journey.student_goals) 
              : (response.user_journey.student_goals || []);
            
            // Interested subjects
            this.interestedSubjects = typeof response.user_journey.interested_subjects === 'string'
              ? JSON.parse(response.user_journey.interested_subjects)
              : (response.user_journey.interested_subjects || []);
            
            // Mental health concerns
            this.mentalHealthConcerns = typeof response.user_journey.mental_health_concerns === 'string'
              ? JSON.parse(response.user_journey.mental_health_concerns)
              : (response.user_journey.mental_health_concerns || []);
            
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
      },
      error: (error) => {
        console.error('Error fetching user profile:', error);
        this.snackBar.open(
          error.error?.error || 'Failed to load profile. Please try again later.',
          'Close',
          { duration: 3000, horizontalPosition: 'center' }
        );
        this.isLoading = false;
      }
    });
  }

  /**
   * Cycles the gender slider
   */
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

  /**
   * Handle file selection for profile picture
   */
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

  /**
   * Submit the form
   */
  onSubmit(): void {
    if (this.profileForm.invalid) {
      this.snackBar.open('Please correct the errors in the form.', 'Close', {
        duration: 3000, horizontalPosition: 'center'
      });
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
    
    // Study plan
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
        this.snackBar.open('Profile updated successfully!', 'Close', {
          duration: 3000, horizontalPosition: 'center'
        });

        // Update preferred language if changed
        const newPreferredLanguage = this.profileForm.get('preferredLanguage')?.value;
        if (newPreferredLanguage && newPreferredLanguage !== this.preferredLanguage) {
          this.preferredLanguage = newPreferredLanguage;
          localStorage.setItem('preferredLanguage', newPreferredLanguage);
          this.translateContent(newPreferredLanguage);
        }

        this.isSubmitting = false;
      },
      error: (error) => {
        console.error('Error updating profile:', error);
        this.snackBar.open(
          error.error?.error || 'Failed to update profile.',
          'Close',
          { duration: 3000, horizontalPosition: 'center' }
        );
        this.isSubmitting = false;
      }
    });
  }

  /**
   * Trigger file input for avatar
   */
  triggerFileInput(fileInput: HTMLInputElement): void {
    fileInput.click();
  }

  /**
   * Open delete confirmation dialog
   */
  openDeleteConfirmationDialog(): void {
    const dialogRef = this.dialog.open(DeleteConfirmationDialogComponent);
    dialogRef.afterClosed().subscribe(result => {
      if (result === true) {
        this.deleteProfile();
      }
    });
  }

  /**
   * Delete profile
   */
  deleteProfile(): void {
    this.isSubmitting = true;
    this.appService.deleteUserProfile().subscribe(
      response => {
        this.isSubmitting = false;
        this.snackBar.open('Your profile has been deleted successfully.', 'Close', {
          duration: 3000, horizontalPosition: 'center'
        });
        this.appService.signOut();
        this.router.navigate(['/auth/sign-up']);
      },
      error => {
        this.isSubmitting = false;
        this.snackBar.open('An error occurred while deleting your profile.', 'Close', {
          duration: 3000, horizontalPosition: 'center'
        });
      }
    );
  }
}
