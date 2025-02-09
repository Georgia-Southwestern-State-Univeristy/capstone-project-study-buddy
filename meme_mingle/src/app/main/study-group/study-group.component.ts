import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { StudyGroupSidebarComponent } from './study-group-sidebar/study-group-sidebar.component';
import { RouterModule } from '@angular/router';
@Component({
  selector: 'app-study-group',
  standalone: true,
  imports: [CommonModule, StudyGroupSidebarComponent, RouterModule],
  templateUrl: './study-group.component.html',
  styleUrls: ['./study-group.component.scss']
})
export class StudyGroupComponent {

}
