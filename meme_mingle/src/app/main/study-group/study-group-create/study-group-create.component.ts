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
      members: ['']  // Optional field for inviting members at creation time
    });
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
    const membersArray = formValues.members
      ? formValues.members.split(',').map((m: string) => m.trim()).filter((m: string) => m !== '')
      : [];

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
        this.successMessage = response.message || 'Group created successfully!';
        // Reset the form (reinitialize privacy to "public")
        this.groupForm.reset();
        this.groupForm.patchValue({ privacy: 'public' });
        this.selectedFile = null;
        this.loading = false;
        // If the response contains a group ID, store it and generate the invite link.
        if (response.group && response.group._id) {
          this.groupId = response.group._id;
          this.generateInviteLink();
        }
      },
      error: (error) => {
        this.errorMessage = error.error?.error || 'An error occurred. Please try again.';
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
        alert('Invite link copied to clipboard!');
      }).catch(err => {
        console.error('Failed to copy invite link: ', err);
      });
    }
  }
}
