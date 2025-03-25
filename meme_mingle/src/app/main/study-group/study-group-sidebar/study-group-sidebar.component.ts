// src/app/main/study-group/study-group-sidebar/study-group-sidebar.component.ts
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AppService } from 'src/app/app.service';
import { RouterModule, Router } from '@angular/router';
import { SidebarService } from 'src/app/shared/service/study-group-sidebar.service';
import { FormsModule } from '@angular/forms';

@Component({
  selector: 'app-study-group-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule, FormsModule],
  templateUrl: './study-group-sidebar.component.html',
  styleUrls: ['./study-group-sidebar.component.scss']
})
export class StudyGroupSidebarComponent implements OnInit {
  groups: any[] = [];
  filteredGroups: any[] = []; // Store filtered groups
  searchTerm: string = ''; // For search functionality
  loading: boolean = false;
  errorMessage: string = '';
  sidebarVisible: boolean = true; // Tracks sidebar visibility
  toggleIcon: string = '<';
  translatedTexts: { [key: string]: string } = {};
  userId: string = '';
  selectedGroupId: string = '';

  constructor(private appService: AppService, private router: Router, private sidebarService: SidebarService) {}

  ngOnInit(): void {
    this.loadGroups();
    this.userId = localStorage.getItem('user_id') || '';
    this.sidebarService.getSidebarState().subscribe((visible: boolean) => {
      this.sidebarVisible = visible;
    });
  }

  // Filter groups based on search term
  filterGroups(): void {
    if (!this.searchTerm.trim()) {
      this.filteredGroups = [...this.groups];
      return;
    }
    
    const term = this.searchTerm.toLowerCase().trim();
    this.filteredGroups = this.groups.filter(group => 
      group.name.toLowerCase().includes(term) || 
      (group.description && group.description.toLowerCase().includes(term))
    );
  }

  loadGroups(): void {
    this.loading = true;
    this.appService.getGroups().subscribe({
      next: (response: { data: any[] }) => {
        // Assume response.data contains the list of groups
        this.groups = response.data;
        this.filteredGroups = [...this.groups]; // Initialize filtered groups
        console.log('Groups:', this.groups);
        this.loading = false;
      },
      error: (error: any) => {
        this.errorMessage = error.error?.error || 'Error retrieving groups';
        this.loading = false;
      }
    });
  }

  joinGroup(group: any): void {
    console.log('Group data:', group);
    if (!group?.id) {
      this.errorMessage = 'Group ID not found.';
      return;
    }
    if (!this.userId) {
      this.router.navigate(['/auth/sign-in'], { queryParams: { returnUrl: this.router.url } });
      return;
    }
    this.loading = true;
    const payload = {
      group_id: group.id,
      user_id: this.userId
    };
    this.appService.joinGroup(payload).subscribe({
      next: (response) => {
        console.log('Joined group successfully:', response);
        if (!group.members) {
          group.members = [];
        }
        group.members.push(this.userId);
        this.loading = false;
      },
      error: (error) => {
        this.errorMessage = error.error?.error || 'Error joining group.';
        this.loading = false;
      }
    });
  }

  // New methods for toggle and create
  // Toggles the sidebar visibility
  toggleSidebar(): void {
    this.sidebarVisible = !this.sidebarVisible;
    this.toggleIcon = this.sidebarVisible ? '<' : '>';
    this.sidebarService.toggleSidebar(); // Notify service about the change
  }

  openGroupPosts(group: any): void {
    if (group.members?.includes(this.userId)) {
      this.selectedGroupId = group.id;
      this.router.navigate(['/main/study-group/group-posts', group.id]);
    } else {
      console.log('You have not joined this group yet.');
    }
  }
}
