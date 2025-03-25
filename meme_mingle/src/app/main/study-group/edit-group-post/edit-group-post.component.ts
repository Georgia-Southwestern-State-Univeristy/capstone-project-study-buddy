import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AppService } from '../../../../app/app.service';
import { SocketService } from '../../../services/socket.service';
import { CanComponentDeactivate } from '../../../guards/can-deactivate.guard';

@Component({
  standalone: true,
  selector: 'app-edit-group-post',
  imports: [
    CommonModule,
    FormsModule
  ],
  templateUrl: './edit-group-post.component.html',
  styleUrls: ['./edit-group-post.component.scss']
})
export class EditGroupPostComponent implements OnInit, CanComponentDeactivate {
  groupId: string = '';
  postId: string = '';
  userId: string = '';
  postContent: string = '';
  originalContent: string = '';
  loading: boolean = true;
  updating: boolean = false;
  errorMessage: string | null = null;
  successMessage: string | null = null;
  post: any = null;
  
  // Attachment handling properties
  attachments: string[] = [];
  originalAttachments: string[] = [];
  newAttachments: File[] = [];
  deletedAttachments: string[] = [];
  maxFileSize: number = 10 * 1024 * 1024; // 10MB
  uploadError: string | null = null;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private appService: AppService,
    private socketService: SocketService
  ) {}

  ngOnInit(): void {
    this.userId = localStorage.getItem('user_id') || '';
    
    // Get query parameters
    this.route.queryParams.subscribe(params => {
      this.groupId = params['groupId'];
      this.postId = params['postId'];
      
      if (!this.groupId || !this.postId) {
        this.errorMessage = "Missing required parameters";
        this.loading = false;
        return;
      }
      
      this.fetchPostDetails();
    });
  }

  fetchPostDetails(): void {
    // Since there's no direct API to get a single post, we'll fetch all group posts
    // and find the one we need
    this.loading = true;
    this.errorMessage = null;
    
    this.appService.getGroupPosts(this.groupId).subscribe({
      next: (response) => {
        const posts = response.data || [];
        this.post = posts.find((p: any) => p._id === this.postId);
        
        if (this.post) {
          // Check if user is the post owner
          if (this.post.user_id !== this.userId) {
            this.errorMessage = "You don't have permission to edit this post";
            this.loading = false;
            return;
          }
          
          this.postContent = this.post.content;
          this.originalContent = this.post.content;
          
          // Initialize attachments
          this.attachments = [...(this.post.attachments || [])];
          this.originalAttachments = [...this.attachments];
          
          this.loading = false;
        } else {
          this.errorMessage = "Post not found";
          this.loading = false;
        }
      },
      error: (error) => {
        console.error('Error fetching post:', error);
        this.errorMessage = error?.error?.error || 'An error occurred while fetching the post.';
        this.loading = false;
      }
    });
  }

  updatePost(): void {
    if (!this.postContent.trim()) {
      this.errorMessage = "Post content cannot be empty";
      return;
    }
    
    // Check if any changes were made
    const hasContentChanges = this.postContent !== this.originalContent;
    const hasAttachmentChanges = this.newAttachments.length > 0 || this.deletedAttachments.length > 0;
    
    if (!hasContentChanges && !hasAttachmentChanges) {
      this.navigateBack();
      return;
    }
    
    this.updating = true;
    this.errorMessage = null;
    
    // Create FormData for the request
    const formData = new FormData();
    formData.append('user_id', this.userId);
    formData.append('content', this.postContent);
    
    // Add new attachments
    if (this.newAttachments.length > 0) {
      for (const file of this.newAttachments) {
        formData.append('files[]', file);
      }
    }
    
    // Add attachments to keep (not deleted)
    if (this.deletedAttachments.length > 0) {
      formData.append('keep_attachments', JSON.stringify(
        this.attachments.filter(url => !this.deletedAttachments.includes(url))
      ));
    }
    
    // Add deleted attachments to remove from storage
    if (this.deletedAttachments.length > 0) {
      formData.append('deleted_attachments', JSON.stringify(this.deletedAttachments));
    }
    
    this.appService.updateGroupPost(this.postId, formData).subscribe({
      next: (response: { message: string }) => {
        this.successMessage = "Post updated successfully!";
        this.updating = false;
        
        // Navigate back after a brief delay
        setTimeout(() => this.navigateBack(), 1500);
      },
      error: (error: { error: { error: string } }) => {
        console.error('Error updating post:', error);
        this.errorMessage = error?.error?.error || 'An error occurred while updating the post.';
        this.updating = false;
      }
    });
  }

  navigateBack(): void {
    this.router.navigate(['/main/study-group/group-posts', this.groupId]);
    console.log('Navigating back to group:', this.groupId);
  }

  // File upload handling
  onFileSelected(event: any): void {
    this.uploadError = null;
    const files: FileList = event.target.files;
    
    if (files && files.length > 0) {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        
        // Check file size
        if (file.size > this.maxFileSize) {
          this.uploadError = `File ${file.name} is too large. Maximum size is 10MB.`;
          continue;
        }
        
        // Add to new attachments
        this.newAttachments.push(file);
      }
      
      // Reset the file input
      event.target.value = '';
    }
  }
  
  // Remove a new attachment that was just added
  removeNewAttachment(index: number): void {
    this.newAttachments.splice(index, 1);
  }
  
  // Mark an existing attachment for deletion
  deleteAttachment(url: string): void {
    // Add to deletedAttachments if it's an original attachment
    if (this.originalAttachments.includes(url)) {
      this.deletedAttachments.push(url);
    }
    
    // Remove from current attachments
    const index = this.attachments.indexOf(url);
    if (index > -1) {
      this.attachments.splice(index, 1);
    }
  }
  
  // Restore a deleted attachment
  undoDeleteAttachment(url: string): void {
    // Remove from deletedAttachments
    const index = this.deletedAttachments.indexOf(url);
    if (index > -1) {
      this.deletedAttachments.splice(index, 1);
      
      // Add back to attachments if it's not already there
      if (!this.attachments.includes(url)) {
        this.attachments.push(url);
      }
    }
  }

  // Check if form has been modified
  isFormDirty(): boolean {
    return this.postContent !== this.originalContent || 
           this.newAttachments.length > 0 || 
           this.deletedAttachments.length > 0;
  }

  // Confirm before leaving if there are unsaved changes
  canDeactivate(): boolean {
    if (this.isFormDirty() && !this.updating) {
      return confirm('You have unsaved changes. Are you sure you want to leave?');
    }
    return true;
  }

  // Check if the attachment is an image file
  isImageFile(url: string): boolean {
    const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp'];
    return imageExtensions.some(ext => url.toLowerCase().endsWith(ext));
  }

  // Get icon based on file type
  getFileIcon(url: string): string {
    const fileName = this.getFileName(url).toLowerCase();
    
    if (fileName.endsWith('.pdf')) {
      return 'bi-file-earmark-pdf';
    } else if (fileName.endsWith('.doc') || fileName.endsWith('.docx')) {
      return 'bi-file-earmark-word';
    } else if (fileName.endsWith('.xls') || fileName.endsWith('.xlsx')) {
      return 'bi-file-earmark-excel';
    } else if (fileName.endsWith('.ppt') || fileName.endsWith('.pptx')) {
      return 'bi-file-earmark-slides';
    } else if (fileName.endsWith('.zip') || fileName.endsWith('.rar')) {
      return 'bi-file-earmark-zip';
    } else if (this.isImageFile(fileName)) {
      return 'bi-file-earmark-image';
    } else {
      return 'bi-file-earmark-text';
    }
  }

  // Extract filename from URL
  getFileName(url: string): string {
    try {
      const parsedUrl = new URL(url);
      const pathSegments = parsedUrl.pathname.split('/');
      const filename = pathSegments[pathSegments.length - 1];
      return decodeURIComponent(filename);
    } catch (error) {
      const segments = url.split('/');
      const filename = segments[segments.length - 1];
      return filename.split('?')[0];
    }
  }
  
  // Get file type to preview new attachments
  getFileType(file: File): string {
    if (file.type.startsWith('image/')) {
      return 'image';
    } else if (file.type === 'application/pdf') {
      return 'pdf';
    } else if (file.type.includes('word') || file.type.includes('doc')) {
      return 'word';
    } else if (file.type.includes('excel') || file.type.includes('sheet')) {
      return 'excel';
    } else if (file.type.includes('powerpoint') || file.type.includes('presentation')) {
      return 'powerpoint';
    } else if (file.type.includes('zip') || file.type.includes('rar')) {
      return 'archive';
    } else {
      return 'other';
    }
  }
  
  // Create Object URL for preview
  getObjectUrl(file: File): string {
    return URL.createObjectURL(file);
  }
  
  // Check if existing attachment is marked for deletion
  isMarkedForDeletion(url: string): boolean {
    return this.deletedAttachments.includes(url);
  }
}