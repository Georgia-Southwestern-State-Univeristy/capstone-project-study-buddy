import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute, Router } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { AppService } from 'src/app/app.service';
import { SocketService } from 'src/app/services/socket.service';
import { environment } from '../../../shared/environments/environment';
import { Subscription } from 'rxjs';

@Component({
  standalone: true,
  selector: 'app-group-posts-list',
  imports: [
    CommonModule,
    RouterModule,
    HttpClientModule,
    FormsModule
  ],
  templateUrl: './group-posts-list.component.html',
  styleUrls: ['./group-posts-list.component.scss']
})
export class GroupPostsListComponent implements OnInit, OnDestroy {
  groupId!: string;
  group: any = {};
  userId!: string;
  posts: any[] = [];
  loading = false;
  errorMessage: string | null = null;
  userProfilePicture: string = '/assets/img/user_avtar.jpg';
  backendUrl = environment.baseUrl;
  likedPosts: Set<string> = new Set<string>();
  // For comments
  commentText: string = '';
  activeCommentPostId: string | null = null;
  expandedCommentPostIds: Set<string> = new Set<string>();
  userCache: Map<string, any> = new Map<string, any>();
  commentsVisiblePostIds: Set<string> = new Set<string>();
  
  // Socket subscriptions
  private postLikedSubscription?: Subscription;
  private postUnlikedSubscription?: Subscription;
  private postCommentedSubscription?: Subscription;
  private errorSubscription?: Subscription;

  constructor(
    private route: ActivatedRoute,
    private appService: AppService,
    private socketService: SocketService,
    private router: Router
  ) {}
  
  ngOnInit(): void {
    this.userId = localStorage.getItem('user_id') || '';
    this.fetchUserProfile();
    this.route.paramMap.subscribe(params => {
      this.groupId = params.get('groupId') as string;
      this.fetchGroupPosts();
      this.fetchGroupDetails();
      
      // Join the group room for real-time updates
      if (this.userId) {
        this.socketService.joinGroupRoom(this.groupId, this.userId);
      }
    });
    
    // Subscribe to socket events
    this.postLikedSubscription = this.socketService.onPostLiked().subscribe(data => {
      this.handlePostLiked(data);
    });
    
    this.postUnlikedSubscription = this.socketService.onPostUnliked().subscribe(data => {
      this.handlePostUnliked(data);
    });
    
    this.postCommentedSubscription = this.socketService.onPostCommented().subscribe(data => {
      this.handlePostCommented(data);
    });
    
    this.errorSubscription = this.socketService.onError().subscribe(data => {
      this.errorMessage = data.message;
      setTimeout(() => this.errorMessage = null, 3000);
    });
  }
  
  ngOnDestroy(): void {
    // Clean up subscriptions
    this.postLikedSubscription?.unsubscribe();
    this.postUnlikedSubscription?.unsubscribe();
    this.postCommentedSubscription?.unsubscribe();
    this.errorSubscription?.unsubscribe();
  }

  onCreatePost(): void {
    this.router.navigate(['/main/study-group/create-group-post'], {
      queryParams: { groupId: this.groupId },
    });
  }

  // When fetching posts, update the likedPosts set
  fetchGroupPosts(): void {
    this.loading = true;
    this.errorMessage = null;

    this.appService.getGroupPosts(this.groupId)
      .subscribe({
        next: (response) => {
          this.posts = response.data || [];
          
          // Initialize liked posts set
          this.likedPosts.clear();
          this.posts.forEach(post => {
            if (post.liked_by && post.liked_by.includes(this.userId)) {
              this.likedPosts.add(post._id);
            }
          });
          
          console.log('Fetched posts:', this.posts);
          this.loading = false;
        },
        error: (err) => {
          console.error('Error fetching posts:', err);
          this.errorMessage = err?.error?.error || 'An error occurred while fetching group posts.';
          this.loading = false;
        }
      });
  }

// Update the likePost method to add logging
likePost(postId: string): void {
  const isCurrentlyLiked = this.likedPosts.has(postId);
  
  if (isCurrentlyLiked) {
    // Unlike the post
    this.likedPosts.delete(postId);
    this.socketService.likePost(postId, this.userId, false);
  } else {
    // Like the post
    this.likedPosts.add(postId);
    this.socketService.likePost(postId, this.userId, true);
  }
}
  // Check if post is liked by current user
  isPostLiked(postId: string): boolean {
    return this.likedPosts.has(postId);
  }

  // Handle post liked event
  handlePostLiked(data: any): void {
    const postIndex = this.posts.findIndex(post => post._id === data.post_id);
    
    // Update the likedPosts set if this user liked the post
    if (data.user_id === this.userId) {
      this.likedPosts.add(data.post_id);
    }
    
    if (postIndex !== -1) {
      // Use the updated count from the server
      if (data.likes !== undefined) {
        this.posts[postIndex].likes = data.likes;
      } else {
        // Fallback to incrementing
        this.posts[postIndex].likes = (this.posts[postIndex].likes || 0) + 1;
      }
      
      // Add user to liked_by array if not present
      if (!this.posts[postIndex].liked_by) {
        this.posts[postIndex].liked_by = [];
      }
      if (!this.posts[postIndex].liked_by.includes(data.user_id)) {
        this.posts[postIndex].liked_by.push(data.user_id);
      }
    }
  }
  // Handle post unliked event
  handlePostUnliked(data: any): void {
    const postIndex = this.posts.findIndex(post => post._id === data.post_id);
    
    // Update the likedPosts set if this user unliked the post
    if (data.user_id === this.userId) {
      this.likedPosts.delete(data.post_id);
    }
    
    if (postIndex !== -1) {
      // Use the updated count from the server
      if (data.likes !== undefined) {
        this.posts[postIndex].likes = data.likes;
      } else {
        // Fallback to decrementing
        this.posts[postIndex].likes = Math.max(0, (this.posts[postIndex].likes || 0) - 1);
      }
      
      // Remove user from liked_by array
      if (this.posts[postIndex].liked_by && data.user_id) {
        const userIndex = this.posts[postIndex].liked_by.indexOf(data.user_id);
        if (userIndex !== -1) {
          this.posts[postIndex].liked_by.splice(userIndex, 1);
        }
      }
    }
  }
  // Show comment input for a specific post
  showCommentInput(postId: string): void {
    // Make comments visible if they're not already (but don't hide them if they are)
    if (!this.commentsVisiblePostIds.has(postId)) {
      this.commentsVisiblePostIds.add(postId);
    }
    
    // Then toggle comment input if necessary
    this.activeCommentPostId = this.activeCommentPostId === postId ? null : postId;
    this.commentText = '';
  }
  
  // Update your submitComment method:
  submitComment(postId: string): void {
  if (!this.commentText.trim()) {
    return;
  }
  
  // Pass the user ID along with the comment
  this.socketService.commentPost(postId, this.commentText, this.userId);
  this.commentText = '';
}
  
  // Handle post commented event
  handlePostCommented(data: any): void {
    const postIndex = this.posts.findIndex(post => post._id === data.post_id);
    if (postIndex !== -1) {
      // Use the updated count from the server if available
      if (data.comments !== undefined) {
        this.posts[postIndex].comments = data.comments;
      } else {
        // Fallback to incrementing
        this.posts[postIndex].comments = (this.posts[postIndex].comments || 0) + 1;
      }
      
      // Add the comment to the comment_list if it exists
      if (this.posts[postIndex].comment_list && data.comment) {
        const newComment = {
          user_id: data.user_id || 'Anonymous',
          content: data.comment,
          created_at: new Date()
        };
        
        if (!Array.isArray(this.posts[postIndex].comment_list)) {
          this.posts[postIndex].comment_list = [];
        }
        
        this.posts[postIndex].comment_list.push(newComment);
      }
    }
  }

  // Get the appropriate profile picture for a post
getProfilePicture(post: any): string {
  // Check if post has user profile information
  if (post.user_profile && post.user_profile.profile_picture) {
    // Check if it's a full URL or just a path
    const profilePic = post.user_profile.profile_picture;
    return profilePic.startsWith('http') ? profilePic : `${this.backendUrl}${profilePic}`;
  }
  
  // Fallback to default
  return '/assets/img/user_avtar.jpg';
}

// Handle image loading errors
handleProfilePictureError(event: any): void {
  event.target.src = '/assets/img/user_avtar.jpg';
}

// Get display name for the post author
getDisplayName(post: any): string {
  if (post.user_profile) {
    // Prefer the user's real name if available, otherwise username
    return post.user_profile.name || post.user_profile.username || post.user_id || 'Anonymous';
  }
  return post.user_id || 'Anonymous';
}

// Format the date for display
formatDate(dateString: string): string {
  if (!dateString) return '';
  const date = new Date(dateString);
  return date.toLocaleString();
}

// Toggle showing all comments for a post
toggleComments(postId: string): void {
  if (this.expandedCommentPostIds.has(postId)) {
    this.expandedCommentPostIds.delete(postId);
  } else {
    this.expandedCommentPostIds.add(postId);
  }
}

// Get comments to display (all if expanded, otherwise just the latest 3)
getDisplayComments(post: any): any[] {
  if (!post.comment_list || !Array.isArray(post.comment_list)) {
    return [];
  }
  
  // Sort comments by date, newest first
  const sortedComments = [...post.comment_list].sort((a, b) => {
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
  
  // If expanded or less than 3 comments, show all
  if (this.expandedCommentPostIds.has(post._id) || sortedComments.length <= 3) {
    return sortedComments;
  }
  
  // Otherwise show only the latest 3
  return sortedComments.slice(0, 3);
}

// Get profile picture for a commenter
fetchUserProfile(): void {
  this.appService.getUserProfile().subscribe({
    next: (response) => {
      
      // Construct the full URL for the profile picture
      if (response.profile_picture) {
        this.userProfilePicture = response.profile_picture.startsWith('http') 
          ? response.profile_picture 
          : `${this.backendUrl}${response.profile_picture}`;
        console.log('User profile picture:', this.userProfilePicture);
      } else {
        this.userProfilePicture = '/assets/img/user_avtar.jpg'; // Fallback image
      }

    },
    error: (error) => {
      console.error('Error fetching user profile:', error);
      this.userProfilePicture = '/assets/img/user_avtar.jpg'; // Fallback image
    },
  });
}

// Get display name for a commenter
getUserDisplayName(userId: string): string {
  // Try to get from cache first
  if (this.userCache.has(userId)) {
    const user = this.userCache.get(userId);
    return user.name || user.username || userId;
  }
  
  // For each post, check if we can find this user
  for (const post of this.posts) {
    if (post.user_id === userId && post.user_profile) {
      // Cache this user's info
      this.userCache.set(userId, post.user_profile);
      return post.user_profile.name || post.user_profile.username || userId;
    }
  }
  
  return userId;
}

// Toggle visibility of comments section
toggleCommentsVisibility(postId: string): void {
  if (this.commentsVisiblePostIds.has(postId)) {
    this.commentsVisiblePostIds.delete(postId);
    
    // Also hide the comment input if it's currently active for this post
    if (this.activeCommentPostId === postId) {
      this.activeCommentPostId = null;
    }
  } else {
    this.commentsVisiblePostIds.add(postId);
  }
}

// Check if comments are visible for a post
areCommentsVisible(postId: string): boolean {
  return this.commentsVisiblePostIds.has(postId);
}

fetchGroupDetails(): void {
  this.appService.getGroups().subscribe({
    next: (response: { data: any[] }) => {
      const foundGroup = response.data.find(g => g.id === this.groupId);
      if (foundGroup) {
        this.group = foundGroup;
        console.log('Group details:', this.group);
      } else {
        console.error('Group not found with ID:', this.groupId);
      }
    },
    error: (error) => {
      console.error('Error fetching group details:', error);
    }
  });
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
  // First try with URL parser
  try {
    const parsedUrl = new URL(url);
    const pathSegments = parsedUrl.pathname.split('/');
    const filename = pathSegments[pathSegments.length - 1];
    // Decode URI components to handle special characters
    return decodeURIComponent(filename);
  } catch (error) {
    // If URL parsing fails, fallback to simple string operations
    const segments = url.split('/');
    const filename = segments[segments.length - 1];
    // Split on query parameters if they exist
    return filename.split('?')[0];
  }
}

// Get human-readable file type
getFileType(url: string): string {
  const fileName = this.getFileName(url).toLowerCase();
  
  if (fileName.endsWith('.pdf')) {
    return 'PDF Document';
  } else if (fileName.endsWith('.doc')) {
    return 'Word Document';
  } else if (fileName.endsWith('.docx')) {
    return 'Word Document';
  } else if (fileName.endsWith('.xls')) {
    return 'Excel Spreadsheet';
  } else if (fileName.endsWith('.xlsx')) {
    return 'Excel Spreadsheet';
  } else if (fileName.endsWith('.ppt')) {
    return 'PowerPoint Presentation';
  } else if (fileName.endsWith('.pptx')) {
    return 'PowerPoint Presentation';
  } else if (fileName.endsWith('.zip')) {
    return 'ZIP Archive';
  } else if (fileName.endsWith('.rar')) {
    return 'RAR Archive';
  } else if (fileName.endsWith('.txt')) {
    return 'Text Document';
  } else if (this.isImageFile(fileName)) {
    return 'Image';
  } else {
    // Extract extension
    const extension = fileName.split('.').pop() || '';
    return extension.toUpperCase() + ' File';
  }
}
}