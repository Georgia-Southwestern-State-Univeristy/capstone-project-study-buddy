import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AppService } from '../../../app.service';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-leaderboard',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatIconModule],
  templateUrl: './leaderboard.component.html',
  styleUrls: ['./leaderboard.component.scss']
})
export class LeaderboardComponent implements OnInit {
  leaderboardData: any[] = [];

  constructor(private appService: AppService) {}

  ngOnInit() {
    this.getLeaderboard();
  }

  getLeaderboard() {
    this.appService.getLeaderboard().subscribe({
      next: (data) => {
        this.leaderboardData = data.leaderboard || [];
      },
      error: (err) => {
        console.error('Error fetching leaderboard:', err);
      },
    });
  }
}