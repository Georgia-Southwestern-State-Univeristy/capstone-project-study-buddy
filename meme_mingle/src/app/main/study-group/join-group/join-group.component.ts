// src/app/main/study-group/join-group/join-group.component.ts
import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { CommonModule } from '@angular/common';  // Import CommonModule
import { AppService } from 'src/app/app.service';

@Component({
  selector: 'app-join-group',
  templateUrl: './join-group.component.html',
  styleUrls: ['./join-group.component.scss'],
  standalone: true,
  imports: [CommonModule]  // Add CommonModule to the imports array
})
export class JoinGroupComponent implements OnInit {
  groupId: string = '';
  message: string = '';
  errorMessage: string = '';
  loading: boolean = false;

  constructor(
    private route: ActivatedRoute,
    private appService: AppService,
    private router: Router
  ) {}

  ngOnInit(): void {
    // Retrieve the group_id query parameter
    this.route.queryParams.subscribe(params => {
      this.groupId = params['group_id'];
      if (this.groupId) {
        this.joinGroup();
      } else {
        this.errorMessage = 'Invalid group link. Group ID not found.';
      }
    });
  }

  joinGroup(): void {
    // Retrieve the current user's ID from localStorage
    const userId = localStorage.getItem('user_id');
    if (!userId) {
      // If the user is not authenticated, redirect them to the sign-in page.
      // Optionally, you can include a return URL so they come back after signing in.
      this.router.navigate(['/auth/sign-in'], { queryParams: { returnUrl: this.router.url } });
      return;
    }

    this.loading = true;
    const payload = {
      group_id: this.groupId,
      user_id: userId
    };

    this.appService.joinGroup(payload).subscribe({
      next: (response) => {
        this.message = response.message || 'You have successfully joined the group!';
        this.loading = false;
      },
      error: (error) => {
        this.errorMessage = error.error?.error || 'An error occurred while joining the group.';
        this.loading = false;
      }
    });
  }
}
