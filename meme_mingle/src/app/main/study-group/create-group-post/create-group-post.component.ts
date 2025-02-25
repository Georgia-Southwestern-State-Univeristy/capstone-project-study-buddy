import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';

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
  
  // Adjust the URL if needed
  private apiUrl = 'http://localhost:8000/group_posts';

  constructor(
    private fb: FormBuilder,
    private http: HttpClient
  ) {
    // Define your form fields, matching the GroupPost model in your backend
    this.postForm = this.fb.group({
      user_id: ['', Validators.required],
      group_id: ['', Validators.required],
      content: ['', Validators.required],
    });
  }

  onSubmit(): void {
    if (this.postForm.valid) {
      // Capture form values
      const postData = this.postForm.value;

      // Send POST request to the Flask endpoint
      this.http.post<any>(this.apiUrl, postData)
        .subscribe({
          next: (response) => {
            // Successfully created the post
            this.successMessage = response.message || 'Post created successfully!';
            this.errorMessage = null;
            // Optionally reset the form
            this.postForm.reset();
          },
          error: (err) => {
            // Handle error
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
