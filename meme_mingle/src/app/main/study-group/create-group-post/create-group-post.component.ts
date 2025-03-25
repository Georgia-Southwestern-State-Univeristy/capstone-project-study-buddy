import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { Location } from '@angular/common';
import { AppService } from '../../../app.service';
import { environment } from '../../../shared/environments/environment';

@Component({
  standalone: true,
  selector: 'app-create-group-post',
  imports: [
    CommonModule,
    HttpClientModule,
    ReactiveFormsModule,
  ],
  templateUrl: './create-group-post.component.html',
  styleUrls: ['./create-group-post.component.scss']
})
export class CreateGroupPostComponent {
  postForm: FormGroup;
  successMessage: string | null = null;
  errorMessage: string | null = null;
  selectedFiles: File[] = [];
  previewUrls: string[] = [];
  isSubmitting = false;
  
  // Adjust the URL if needed
  private apiUrl = environment.baseUrl + '/group_posts';

  constructor(
    private fb: FormBuilder,
    private http: HttpClient,
    private route: ActivatedRoute,
    private location: Location,
    private appService: AppService
  ) {
    this.postForm = this.fb.group({
      user_id: [''],
      group_id: [''],
      content: ['', Validators.required],
    });
  }
  
  ngOnInit(): void {
    const userId = localStorage.getItem('user_id') || '';
    this.route.queryParams.subscribe((params) => {
      const grpId = params['groupId'] || '';
      this.postForm.patchValue({
        user_id: userId,
        group_id: grpId
      });
    });
  }
  
  onBack(): void {
    this.location.back();
  }

  onFilesSelected(event: any): void {
    const files = event.target.files;
    
    if (files) {
      // Clear previous selections
      this.selectedFiles = [];
      this.previewUrls = [];
      
      // Store and create previews for each file
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        this.selectedFiles.push(file);
        
        // Create preview URLs for images
        if (file.type.startsWith('image/')) {
          const reader = new FileReader();
          reader.onload = (e: any) => {
            this.previewUrls.push(e.target.result);
          };
          reader.readAsDataURL(file);
        } else {
          // For non-image files, just show the filename
          this.previewUrls.push('assets/file-icon.png');
        }
      }
    }
  }

  removeFile(index: number): void {
    this.selectedFiles.splice(index, 1);
    this.previewUrls.splice(index, 1);
  }

  onSubmit(): void {
    if (this.postForm.valid) {
      this.isSubmitting = true;
      
      // Create FormData object to handle files
      const formData = new FormData();
      
      // Add form fields
      formData.append('user_id', this.postForm.get('user_id')?.value);
      formData.append('group_id', this.postForm.get('group_id')?.value);
      formData.append('content', this.postForm.get('content')?.value);
      
      // Add files if any
      if (this.selectedFiles.length > 0) {
        for (const file of this.selectedFiles) {
          formData.append('files[]', file);
        }
      }

      // Send POST request with FormData or JSON depending on files
      let request;
      if (this.selectedFiles.length > 0) {
        // If we have files, send FormData
        request = this.http.post<any>(this.apiUrl, formData);
      } else {
        // If no files, send JSON
        request = this.http.post<any>(this.apiUrl, this.postForm.value);
      }
      
      request.subscribe({
        next: (response) => {
          // Successfully created the post
          this.successMessage = response.message || 'Post created successfully!';
          this.errorMessage = null;
          // Reset form and file selections
          this.postForm.reset();
          this.selectedFiles = [];
          this.previewUrls = [];
          this.isSubmitting = false;
          
          // Navigate back after a short delay
          setTimeout(() => {
            this.location.back();
          }, 1500);
        },
        error: (err) => {
          // Handle error
          this.isSubmitting = false;
          this.successMessage = null;
          // Show a more specific error message if available
          this.errorMessage = err?.error?.error || 'An error occurred while creating the post.';
        }
      });
    } else {
      // Mark all fields as touched to show validation errors
      this.postForm.markAllAsTouched();
    }
  }
}
