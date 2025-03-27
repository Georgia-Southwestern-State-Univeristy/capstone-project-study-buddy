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
  
  // For post options dropdown
  activeOptionsPostId: string | null = null;
  hiddenPostIds: Set<string> = new Set<string>();
  
  // Translation properties
  preferredLanguage: string = 'en';
  translatedTexts: { [key: string]: string } = {};
  originalPostContents: Map<string, string> = new Map<string, string>(); // Store original content to avoid multiple translations
  translationInProgress: boolean = false;
  
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
    this.loadHiddenPosts(); // Load hidden posts from local storage
    
    // Load preferred language from localStorage
    this.preferredLanguage = localStorage.getItem('preferredLanguage') || 'en';
    
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
    
    // If user's language is not English, do an initial pass of translation
    if (this.preferredLanguage !== 'en') {
      this.translateStaticContent();
    }
  }
  
  ngAfterViewInit(): void {
    // After view initialization, translate any dynamic content
    setTimeout(() => {
      if (this.preferredLanguage !== 'en') {
        this.translateDynamicContent();
      }
    }, 300);
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
          // Filter out hidden posts
          this.posts = (response.data || []).filter((post: any) => 
            !this.hiddenPostIds.has(post._id)
          );
          
          // Initialize liked posts set
          this.likedPosts.clear();
          this.posts.forEach(post => {
            if (post.liked_by && post.liked_by.includes(this.userId)) {
              this.likedPosts.add(post._id);
            }
            
            // Store original post content for translation
            if (post.content) {
              this.originalPostContents.set(post._id, post.content);
            }
          });
          
          this.loading = false;
          
          // Translate post content if needed
          if (this.preferredLanguage !== 'en' && this.posts.length > 0) {
            this.translatePostContent();
          }
        },
        error: (err) => {
          console.error('Error fetching posts:', err);
          this.errorMessage = err?.error?.error || 'An error occurred while fetching group posts.';
          this.loading = false;
        }
      });
  }

  // =========================================
  // Translation Methods
  // =========================================
  
  /**
   * Translate all static content on the page
   */
  private translateStaticContent(): void {
    // 1) Grab the text from all elements marked with data-translate
    const elementsToTranslate = document.querySelectorAll('[data-translate]');
    const textsInDom = Array.from(elementsToTranslate).map(
      (el) => el.textContent?.trim() || ''
    );

    // 2) Include additional strings you might need from code
    const additionalTexts = [
      'Group Posts',
      'Create Post',
      'Loading posts...',
      'No posts found for this group. Be the first to create one!',
      'Edit Post',
      'Delete Post',
      'Hide Post',
      'Posts',
      'Attachments',
      'Like',
      'Comments',
      'Hide Comments',
      'View all',
      'Hide',
      'comments',
      'comment',
      'Write a comment...',
      'Add a comment',
      'Be the first to create one!',
      'Are you sure you want to delete this post? This action cannot be undone.'
    ];

    // Combine them into a unique set
    const combinedSet = new Set([...textsInDom, ...additionalTexts].filter(Boolean));
    const allTextsToTranslate = Array.from(combinedSet);

    // If nothing to translate, skip
    if (!allTextsToTranslate.length) {
      return;
    }

    // 3) Call the translation service
    this.appService.translateTexts(allTextsToTranslate, this.preferredLanguage).subscribe({
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
  
  /**
   * Translate any dynamic content that might have been added after initial load
   */
  private translateDynamicContent(): void {
    if (this.preferredLanguage === 'en') return;
    
    const elementsToTranslate = document.querySelectorAll('[data-translate]');
    const textsInDom = Array.from(elementsToTranslate).map(
      (el) => el.textContent?.trim() || ''
    );

    // Filter out any texts we already have translations for
    const notYetTranslated = textsInDom.filter(t => !this.translatedTexts[t] && t !== '');

    if (!notYetTranslated.length) {
      // Everything is either translated or empty
      // Just reassign to be safe
      elementsToTranslate.forEach((element) => {
        const text = element.textContent?.trim() || '';
        if (this.translatedTexts[text]) {
          element.textContent = this.translatedTexts[text];
        }
      });
      return;
    }

    // Call translation service for the new strings
    this.appService.translateTexts(notYetTranslated, this.preferredLanguage)
      .subscribe({
        next: (response) => {
          const translations = response.translations;
          notYetTranslated.forEach((original, i) => {
            this.translatedTexts[original] = translations[i];
          });
          // Update the DOM
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
  
  /**
   * Translate the content of posts and comments
   */
  private translatePostContent(): void {
    if (this.preferredLanguage === 'en' || this.translationInProgress || this.posts.length === 0) {
      return;
    }
    
    this.translationInProgress = true;
    
    // Collect all text that needs translation
    const textsToTranslate: string[] = [];
    const textSources: {postId: string, type: 'post'|'comment', index?: number}[] = [];
    
    // Add post content
    this.posts.forEach(post => {
      if (post.content && post.content.trim() !== '') {
        textsToTranslate.push(post.content);
        textSources.push({ postId: post._id, type: 'post' });
      }
      
      // Add comment content if available
      if (post.comment_list && Array.isArray(post.comment_list)) {
        post.comment_list.forEach((comment: any, index: number) => {
          if (comment.content && comment.content.trim() !== '') {
            textsToTranslate.push(comment.content);
            textSources.push({ postId: post._id, type: 'comment', index });
          }
        });
      }
    });
    
    if (textsToTranslate.length === 0) {
      this.translationInProgress = false;
      return;
    }
    
    // Call translation service
    this.appService.translateTexts(textsToTranslate, this.preferredLanguage).subscribe({
      next: (response) => {
        const translations = response.translations;
        
        // Apply translations to posts and comments
        translations.forEach((translation: string, idx: number) => {
          const source = textSources[idx];
          
          if (source.type === 'post') {
            // Find post and update content
            const post = this.posts.find(p => p._id === source.postId);
            if (post) {
              post.content = translation;
            }
          } else if (source.type === 'comment' && typeof source.index === 'number') {
            // Find post and update comment
            const post = this.posts.find(p => p._id === source.postId);
            if (post && post.comment_list && Array.isArray(post.comment_list) && 
                post.comment_list.length > source.index) {
              post.comment_list[source.index].content = translation;
            }
          }
        });
        
        this.translationInProgress = false;
      },
      error: (err) => {
        console.error('Error translating post content:', err);
        this.translationInProgress = false;
      }
    });
  }

  // Restore original post content (if user switches back to English)
  private restoreOriginalContent(): void {
    this.posts.forEach(post => {
      const originalContent = this.originalPostContents.get(post._id);
      if (originalContent) {
        post.content = originalContent;
      }
    });
  }

  // Handle post liked event
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
  
  // Submit comment
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
      if (data.comment) {
        const newComment = {
          user_id: data.user_id || 'Anonymous',
          content: data.comment,
          created_at: new Date()
        };
        
        if (!this.posts[postIndex].comment_list) {
          this.posts[postIndex].comment_list = [];
        }
        
        this.posts[postIndex].comment_list.push(newComment);
        
        // Translate the new comment if needed
        if (this.preferredLanguage !== 'en') {
          this.translateNewComment(postIndex, this.posts[postIndex].comment_list.length - 1);
        }
      }
    }
  }
  
  // Translate a newly added comment
  translateNewComment(postIndex: number, commentIndex: number): void {
    if (this.preferredLanguage === 'en' || !this.posts[postIndex]?.comment_list?.[commentIndex]) {
      return;
    }
    
    const comment = this.posts[postIndex].comment_list[commentIndex];
    const textToTranslate = comment.content;
    
    if (!textToTranslate || textToTranslate.trim() === '') {
      return;
    }
    
    this.appService.translateTexts([textToTranslate], this.preferredLanguage).subscribe({
      next: (response) => {
        if (response.translations && response.translations.length > 0) {
          comment.content = response.translations[0];
        }
      },
      error: (err) => console.error('Error translating new comment:', err)
    });
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
        } else {
          this.userProfilePicture = '/assets/img/user_avtar.jpg'; // Fallback image
        }

        // Check if the user has a preferred language
        if (response.preferredLanguage) {
          const newPreferredLanguage = response.preferredLanguage;
          if (newPreferredLanguage !== this.preferredLanguage) {
            this.preferredLanguage = newPreferredLanguage;
            
            if (this.preferredLanguage === 'en') {
              this.restoreOriginalContent();
            } else {
              this.translateStaticContent();
              this.translatePostContent();
            }
          }
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
          
          // Update title after group details are loaded and trigger translation if needed
          setTimeout(() => {
            if (this.preferredLanguage !== 'en') {
              this.translateDynamicContent();
            }
          }, 100);
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

  // Toggle post options menu
  togglePostOptions(postId: string, event: Event): void {
    event.stopPropagation(); // Prevent event bubbling
    this.activeOptionsPostId = this.activeOptionsPostId === postId ? null : postId;
    
    // Close dropdown when clicking outside
    if (this.activeOptionsPostId) {
      const closeDropdown = (e: any) => {
        if (!e.target.closest('.post-options')) {
          this.activeOptionsPostId = null;
          document.removeEventListener('click', closeDropdown);
        }
      };
      
      setTimeout(() => {
        document.addEventListener('click', closeDropdown);
      }, 0);
    }
  }

  // Check if current user is the post owner
  isPostOwner(post: any): boolean {
    return post.user_id === this.userId;
  }

  // Edit post
  editPost(post: any): void {
    // Close the options menu before navigating
    this.activeOptionsPostId = null;
    
    // Navigate to edit post page with post information
    this.router.navigate(['/main/study-group/edit-group-post'], {
      queryParams: { 
        groupId: this.groupId,
        postId: post._id 
      },
    });
  }

  // Confirm delete post
  confirmDeletePost(postId: string): void {
    const confirmMessage = this.translatedTexts['Are you sure you want to delete this post? This action cannot be undone.'] || 
      'Are you sure you want to delete this post? This action cannot be undone.';
      
    if (confirm(confirmMessage)) {
      this.deletePost(postId);
    }
  }

  // Delete post
  deletePost(postId: string): void {
    this.appService.deleteGroupPost(postId, this.userId).subscribe({
      next: (response) => {
        console.log('Post deleted successfully:', response);
        // Remove post from UI
        this.posts = this.posts.filter(post => post._id !== postId);
        this.activeOptionsPostId = null;
      },
      error: (error) => {
        console.error('Error deleting post:', error);
        this.errorMessage = error?.error?.error || 'Failed to delete post. Please try again.';
        setTimeout(() => this.errorMessage = null, 3000);
      }
    });
  }

  // Hide post for current user
  hidePost(postId: string): void {
    this.hiddenPostIds.add(postId);
    this.activeOptionsPostId = null;
    
    // Optimistically remove post from UI
    this.posts = this.posts.filter(post => !this.hiddenPostIds.has(post._id));
    
    // Store hidden posts in local storage for persistence
    localStorage.setItem('hidden_posts', JSON.stringify([...this.hiddenPostIds]));
  }

  // Load hidden posts from local storage
  loadHiddenPosts(): void {
    const hiddenPosts = localStorage.getItem('hidden_posts');
    if (hiddenPosts) {
      try {
        const parsedIds = JSON.parse(hiddenPosts);
        this.hiddenPostIds = new Set(parsedIds);
      } catch (e) {
        console.error('Error parsing hidden posts:', e);
      }
    }
  }
}