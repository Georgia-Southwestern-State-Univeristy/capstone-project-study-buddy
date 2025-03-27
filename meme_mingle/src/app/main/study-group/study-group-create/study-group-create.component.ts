// src/app/main/study-group/study-group-create/study-group-create.component.ts
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { AppService } from 'src/app/app.service';

@Component({
  selector: 'app-study-group-create',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './study-group-create.component.html',
  styleUrls: ['./study-group-create.component.scss']
})
export class StudyGroupCreateComponent implements OnInit {
  groupForm!: FormGroup;
  loading = false;
  successMessage: string = '';
  errorMessage: string = '';
  inviteLink: string = '';
  groupId: string = '';
  selectedFile: File | null = null;
  
  // New properties for user dropdown
  users: any[] = [];
  filteredUsers: any[] = [];
  searchTerm: string = '';
  selectedMembers: any[] = [];

  // Translation related properties
  preferredLanguage: string = 'en';
  translatedTexts: { [key: string]: string } = {};

  constructor(private fb: FormBuilder, private appService: AppService) {}

  ngOnInit(): void {
    // Initialize the reactive form with validations.
    this.groupForm = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(3), Validators.maxLength(50)]],
      description: [''],
      topics: [''],
      privacy: ['public', Validators.required],
      rules: [''],
      image_url: [''],
      members: ['']  // We'll still use this control but populate it differently
    });
    
    // Fetch users for the dropdown
    this.loadUsers();
    
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
      'Create a New Study Group',
      'Group Name',
      'Enter a memorable name for your group',
      'Group name is required.',
      'Group name must be at least 3 characters.',
      'Group name cannot exceed 50 characters.',
      'Description',
      'What is this group about? What will members learn?',
      'Topics',
      'e.g., Calculus, Physics, Literature (comma separated)',
      'Add relevant topics to help others find your group',
      'Privacy Setting',
      'Public - Anyone can find and join',
      'Private - Members need an invitation',
      'You can change this setting later',
      'Group Rules',
      'Be respectful, No spam, Keep on topic (comma separated)',
      'Rules help set expectations for group members',
      'Group Image',
      'Enter image URL',
      'Or upload an image file below',
      'Max size: 5MB',
      'Invite Members',
      'Search for users by username...',
      'Share your group with classmates right away',
      'Creating...',
      'Create Group',
      'Shareable Invite Link:',
      'Copy',
      'Invite link copied to clipboard!',
      'Failed to load users for invitation',
      'Group created successfully!',
      'An error occurred. Please try again.'
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

  loadUsers(search: string = '') {
    this.appService.getUsersList(search).subscribe({
      next: (response) => {
        this.users = response.data;
        this.filteredUsers = [...this.users];
      },
      error: (error) => {
        console.error('Error fetching users:', error);
        this.errorMessage = this.translatedTexts['Failed to load users for invitation'] || 'Failed to load users for invitation';
      }
    });
  }

  // Filter users based on search input
  filterUsers(event: any) {
    const searchTerm = event.target.value.toLowerCase();
    this.searchTerm = searchTerm;
    
    if (searchTerm) {
      this.filteredUsers = this.users.filter(user => 
        user.username.toLowerCase().includes(searchTerm) || 
        (user.name && user.name.toLowerCase().includes(searchTerm))
      );
    } else {
      this.filteredUsers = [...this.users];
    }
  }

  // Toggle user selection
  toggleUserSelection(user: any) {
    const index = this.selectedMembers.findIndex(m => m.id === user.id);
    
    if (index === -1) {
      // Add user to selected members
      this.selectedMembers.push(user);
    } else {
      // Remove user from selected members
      this.selectedMembers.splice(index, 1);
    }
    
    // Update the form control with selected user IDs
    const memberIds = this.selectedMembers.map(member => member.id);
    this.groupForm.patchValue({ members: memberIds.join(',') });
  }

  isSelected(user: any): boolean {
    return this.selectedMembers.some(m => m.id === user.id);
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile = input.files[0];
      
      // Clear the image_url field when a file is selected
      if (this.selectedFile) {
        this.groupForm.patchValue({ image_url: '' });
      }
    }
  }

  onSubmit() {
    // Prevent submission if the form is invalid.
    if (this.groupForm.invalid) {
      return;
    }
    this.loading = true;
    this.successMessage = '';
    this.errorMessage = '';
    this.inviteLink = '';
    this.groupId = '';

    const formValues = this.groupForm.value;
    
    // Convert comma-separated fields into arrays
    const topicsArray = formValues.topics
      ? formValues.topics.split(',').map((t: string) => t.trim()).filter((t: string) => t !== '')
      : [];
    const rulesArray = formValues.rules
      ? formValues.rules.split(',').map((r: string) => r.trim()).filter((r: string) => r !== '')
      : [];
      
    // Use selected member IDs from our array
    const membersArray = this.selectedMembers.map(member => member.id);

    // Retrieve the current user's ID (assumed stored in localStorage)
    const createdBy = localStorage.getItem('user_id') || 'default_user';

    // Create a FormData object for file upload support
    const formData = new FormData();
    formData.append('name', formValues.name);
    formData.append('description', formValues.description || '');
    formData.append('privacy', formValues.privacy);
    formData.append('created_by', createdBy);
    
    // Append arrays as JSON strings
    formData.append('topics', JSON.stringify(topicsArray));
    formData.append('rules', JSON.stringify(rulesArray));
    formData.append('members', JSON.stringify(membersArray));
    
    // Add either the image URL or the file, not both
    if (formValues.image_url) {
      formData.append('image_url', formValues.image_url);
    } else if (this.selectedFile) {
      formData.append('group_image', this.selectedFile, this.selectedFile.name);
    }

    // Call the createGroup method in the AppService with FormData
    this.appService.createGroup(formData).subscribe({
      next: (response) => {
        this.successMessage = this.translatedTexts['Group created successfully!'] || response.message || 'Group created successfully!';
        // Reset the form (reinitialize privacy to "public")
        this.groupForm.reset();
        this.groupForm.patchValue({ privacy: 'public' });
        this.selectedFile = null;
        this.selectedMembers = []; // Clear selected members
        this.loading = false;
        // If the response contains a group ID, store it and generate the invite link.
        if (response.group && response.group._id) {
          this.groupId = response.group._id;
          this.generateInviteLink();
        }
      },
      error: (error) => {
        this.errorMessage = this.translatedTexts['An error occurred. Please try again.'] || error.error?.error || 'An error occurred. Please try again.';
        this.loading = false;
      }
    });
  }

  generateInviteLink() {
    // Generate an invite link based on the group ID.
    // Here, we assume that your app has a join-group component at /join-group
    // that will automatically join the group for authenticated users.
    this.inviteLink = `${window.location.origin}/join-group?group_id=${this.groupId}`;
  }

  copyInviteLink() {
    if (this.inviteLink) {
      navigator.clipboard.writeText(this.inviteLink).then(() => {
        alert(this.translatedTexts['Invite link copied to clipboard!'] || 'Invite link copied to clipboard!');
      }).catch(err => {
        console.error('Failed to copy invite link: ', err);
      });
    }
  }
}
