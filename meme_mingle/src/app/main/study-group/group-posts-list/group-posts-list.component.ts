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
  userId!: string;
  posts: any[] = [];
  loading = false;
  errorMessage: string | null = null;
  userProfilePicture: string = '/assets/img/user_avtar.jpg';
  backendUrl = environment.baseUrl;
  
  // For comments
  commentText: string = '';
  activeCommentPostId: string | null = null;
  
  // Socket subscriptions
  private postLikedSubscription?: Subscription;
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
    
    this.route.paramMap.subscribe(params => {
      this.groupId = params.get('groupId') as string;
      this.fetchGroupPosts();
      
      
      // Join the group room for real-time updates
      if (this.userId) {
        this.socketService.joinGroupRoom(this.groupId, this.userId);
      }
    });
    
    // Subscribe to socket events
    this.postLikedSubscription = this.socketService.onPostLiked().subscribe(data => {
      this.handlePostLiked(data);
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
    this.postCommentedSubscription?.unsubscribe();
    this.errorSubscription?.unsubscribe();
  }

  onCreatePost(): void {
    this.router.navigate(['/main/study-group/create-group-post'], {
      queryParams: { groupId: this.groupId },
    });
  }

  // Update the fetchGroupPosts method
fetchGroupPosts(): void {
  this.loading = true;
  this.errorMessage = null;

  this.appService.getGroupPosts(this.groupId)
    .subscribe({
      next: (response) => {
        this.posts = response.data || [];
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
  console.log('Attempting to like post with ID:', postId);
  this.socketService.likePost(postId);
}
  
  // Handle post liked event
  handlePostLiked(data: any): void {
    const postIndex = this.posts.findIndex(post => post._id === data.post_id);
    if (postIndex !== -1) {
      // Use the updated count from the server if available
      if (data.likes !== undefined) {
        this.posts[postIndex].likes = data.likes;
      } else {
        // Fallback to incrementing
        this.posts[postIndex].likes = (this.posts[postIndex].likes || 0) + 1;
      }
    }
  }
  
  // Show comment input for a specific post
  showCommentInput(postId: string): void {
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
}