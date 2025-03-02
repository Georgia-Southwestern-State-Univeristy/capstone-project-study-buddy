import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule } from '@angular/common/http';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { Location } from '@angular/common';

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
    private http: HttpClient,
    private route: ActivatedRoute,
    private location: Location
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
