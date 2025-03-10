import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute, Router } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';
import { AppService } from 'src/app/app.service'; // Adjust path as needed
import { environment } from '../../../shared/environments/environment';
@Component({
  standalone: true,
  selector: 'app-group-posts-list',
  imports: [
    CommonModule,
    RouterModule,
    HttpClientModule
  ],
  templateUrl: './group-posts-list.component.html',
  styleUrls: ['./group-posts-list.component.scss']
})
export class GroupPostsListComponent implements OnInit {
  groupId!: string;
  posts: any[] = [];
  loading = false;
  errorMessage: string | null = null;
  userProfilePicture: string = '/assets/img/user_avtar.jpg';
  backendUrl = environment.baseUrl; 

  constructor(
    private route: ActivatedRoute,
    private appService: AppService,
    private router: Router
  ) {}
  
  onCreatePost(): void {
    this.router.navigate(['/main/study-group/create-group-post'], {
      queryParams: { groupId: this.groupId },
    });
  }

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      this.groupId = params.get('groupId') as string;
      this.fetchGroupPosts();
    });
  }

  fetchGroupPosts(): void {
    this.loading = true;
    this.errorMessage = null;

    this.appService.getGroupPosts(this.groupId)
      .subscribe({
        next: (response) => {
          /*
            The response structure based on your backend:
            {
              message: "Posts retrieved successfully",
              data: [...array of posts...]
            }
          */
          console.log(response);
          this.posts = response.data || [];
          this.loading = false;
        },
        error: (err) => {
          this.errorMessage = err?.error?.error || 'An error occurred while fetching group posts.';
          this.loading = false;
        }
      });
  }

  // Fetch user profile picture
  fetchUserProfile(): void {
    this.appService.getUserProfile().subscribe({
      next: (response) => {
        if (response.profile_picture) {
          this.userProfilePicture = response.profile_picture.startsWith('http')
            ? response.profile_picture
            : `${this.backendUrl}${response.profile_picture}`;
        } else {
          this.userProfilePicture = '/assets/img/user_avtar.jpg';
        }
      },
      error: (error) => {
        console.error('Error fetching user profile:', error);
        this.userProfilePicture = '/assets/img/user_avtar.jpg';
      },
    });
  }

}
