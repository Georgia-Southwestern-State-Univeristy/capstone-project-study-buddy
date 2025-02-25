import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, ActivatedRoute } from '@angular/router';
import { HttpClientModule } from '@angular/common/http';
import { AppService } from 'src/app/app.service'; // Adjust path as needed

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

  constructor(
    private route: ActivatedRoute,
    private appService: AppService
  ) {}

  ngOnInit(): void {
    // 1) Grab the groupId from the route param
    this.groupId = this.route.snapshot.paramMap.get('groupId') as string;
    // 2) Fetch the group posts
    this.fetchGroupPosts();
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
}
