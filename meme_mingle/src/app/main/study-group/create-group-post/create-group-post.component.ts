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
  
  // For translation support
  preferredLanguage: string = 'en';
  translatedTexts: { [key: string]: string } = {};
  
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
    
    // Load user's preferred language from localStorage
    this.preferredLanguage = localStorage.getItem('preferredLanguage') || 'en';
    
    // If user's language is not English, do an initial translation
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
      'Create New Post',
      'What\'s on your mind?',
      'Share your thoughts, questions, or insights with the group...',
      'Add Photos or Files (Optional)',
      'Drop files here or click to browse',
      'Supports images, PDFs, and office documents',
      'Remove file',
      'Posting...',
      'Share Post',
      'Please add some content to your post.',
      'Post created successfully!',
      'An error occurred while creating the post.'
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
          this.successMessage = response.message || this.translatedTexts['Post created successfully!'] || 'Post created successfully!';
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
          this.errorMessage = err?.error?.error || this.translatedTexts['An error occurred while creating the post.'] || 'An error occurred while creating the post.';
        }
      });
    } else {
      // Mark all fields as touched to show validation errors
      this.postForm.markAllAsTouched();
    }
  }
}
