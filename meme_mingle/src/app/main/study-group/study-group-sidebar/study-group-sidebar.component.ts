// src/app/main/study-group/study-group-sidebar/study-group-sidebar.component.ts
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AppService } from 'src/app/app.service';
import { RouterModule, Router } from '@angular/router';
import { SidebarService } from 'src/app/shared/service/study-group-sidebar.service';

@Component({
  selector: 'app-study-group-sidebar',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './study-group-sidebar.component.html',
  styleUrls: ['./study-group-sidebar.component.scss']
})
export class StudyGroupSidebarComponent implements OnInit {
  groups: any[] = [];
  loading: boolean = false;
  errorMessage: string = '';
  sidebarVisible: boolean = true; // Tracks sidebar visibility
  toggleIcon: string = '<';
  translatedTexts: { [key: string]: string } = {};
  userId: string = '';

  constructor(private appService: AppService, private router: Router,  private sidebarService: SidebarService,) {}

  ngOnInit(): void {
    this.loadGroups();
    this.userId = localStorage.getItem('user_id') || '';
    this.sidebarService.getSidebarState().subscribe((visible: boolean) => {
      this.sidebarVisible = visible;
    });
  }

  loadGroups(): void {
    this.loading = true;
    this.appService.getGroups().subscribe({
      next: (response: { data: any[] }) => {
        // Assume response.data contains the list of groups
        this.groups = response.data;
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
    console.log('Join group', group);
    // Additional logic for joining the group can go here
  }

  // New methods for toggle and create
  // Toggles the sidebar visibility
 toggleSidebar(): void {
  this.sidebarVisible = !this.sidebarVisible;
  this.toggleIcon = this.sidebarVisible ? '<' : '>';
  this.sidebarService.toggleSidebar(); // Notify service about the change
}
}
