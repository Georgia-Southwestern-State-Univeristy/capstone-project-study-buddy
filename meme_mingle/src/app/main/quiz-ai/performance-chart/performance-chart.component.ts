import { Component, OnInit, AfterViewInit, Input, OnChanges, SimpleChanges, ViewChild, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Chart, registerables } from 'chart.js';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatIconModule } from '@angular/material/icon';

Chart.register(...registerables);

interface TopicScore {
  topic: string;
  score: number;
  quiz_count: number;
}

@Component({
  selector: 'app-performance-chart',
  standalone: true,
  imports: [CommonModule, MatCardModule, MatProgressSpinnerModule, MatIconModule],
  templateUrl: './performance-chart.component.html',
  styleUrls: ['./performance-chart.component.scss']
})
export class PerformanceChartComponent implements OnInit, AfterViewInit, OnChanges {
  @Input() topicScores: TopicScore[] = [];
  @Input() translatedTexts: { [key: string]: string } = {};
  @Input() isLoading: boolean = true;

  // 1) Instead of IDs, reference the <canvas> via ViewChild:
  @ViewChild('barChartCanvas') barChartCanvas!: ElementRef<HTMLCanvasElement>;
  @ViewChild('doughnutChartCanvas') doughnutChartCanvas!: ElementRef<HTMLCanvasElement>;

  barChart: Chart | null = null;
  doughnutChart: Chart | null = null;

  // Used to retry chart creation if the view is not ready immediately
  private chartInitAttempts = 0;
  private readonly MAX_ATTEMPTS = 5;

  constructor() {}

  ngOnInit(): void {
    console.log('PerformanceChartComponent initialized with data:', this.topicScores);
  }

  // 2) Use ngAfterViewInit to start rendering if data is already present
  ngAfterViewInit(): void {
    console.log('ngAfterViewInit - Topic scores:', this.topicScores);

    // If we already have data when view initializes, attempt chart rendering
    if (!this.isLoading && this.topicScores.length > 0) {
      this.attemptRenderCharts();
    }
  }

  // 3) If @Input data changes, re-render when topicScores arrives
  ngOnChanges(changes: SimpleChanges): void {
    if (changes['topicScores']?.currentValue) {
      console.log('ngOnChanges - Topic scores changed:', changes['topicScores'].currentValue);
      this.isLoading = false;
      this.chartInitAttempts = 0;

      // Wait a tick so Angular renders the <canvas> elements
      setTimeout(() => {
        this.attemptRenderCharts();
      }, 300);
    }
  }

  // Will retry rendering if the canvases were still not in the DOM
  attemptRenderCharts(): void {
    if (this.chartInitAttempts >= this.MAX_ATTEMPTS) {
      console.error('Max chart rendering attempts reached');
      return;
    }

    this.chartInitAttempts++;
    console.log(`Attempt ${this.chartInitAttempts} to render charts`);

    setTimeout(() => {
      try {
        this.renderCharts();
      } catch (err) {
        console.error('Error rendering charts:', err);
        if (this.chartInitAttempts < this.MAX_ATTEMPTS) {
          this.attemptRenderCharts();
        }
      }
    }, 300 * this.chartInitAttempts);
  }

  renderCharts(): void {
    if (!this.topicScores || this.topicScores.length === 0) {
      return; // no data, skip
    }
    console.log('Rendering charts with data:', this.topicScores);

    this.renderBarChart();
    this.renderDoughnutChart();
  }

  renderBarChart(): void {
    // Destroy old instance if it exists
    if (this.barChart) {
      this.barChart.destroy();
    }

    // Grab the <canvas> from ViewChild
    if (!this.barChartCanvas) {
      console.error('Bar chart canvas ViewChild not found');
      return;
    }
    const canvas = this.barChartCanvas.nativeElement;

    console.log('Bar chart canvas found, width/height:', canvas.width, canvas.height);

    try {
      const labels = this.topicScores.map(t => t.topic);
      const data = this.topicScores.map(t => t.score);
      const quizCounts = this.topicScores.map(t => t.quiz_count);

      this.barChart = new Chart(canvas, {
        type: 'bar',
        data: {
          labels,
          datasets: [{
            label: this.translatedTexts['Score'] || 'Score',
            data,
            backgroundColor: 'rgba(255, 184, 77, 0.8)',
            borderColor: 'rgba(255, 184, 77, 1)',
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              display: true,
              position: 'top',
              labels: {
                color: '#ffffff'
              }
            },
            tooltip: {
              callbacks: {
                afterLabel: (context) => {
                  const index = context.dataIndex;
                  return `${this.translatedTexts['Quizzes Taken'] || 'Quizzes Taken'}: ${quizCounts[index]}`;
                }
              }
            }
          },
          scales: {
            y: {
              beginAtZero: true,
              grid: {
                color: 'rgba(255, 255, 255, 0.1)'
              },
              ticks: {
                color: '#ffffff'
              }
            },
            x: {
              grid: {
                color: 'rgba(255, 255, 255, 0.1)'
              },
              ticks: {
                color: '#ffffff'
              }
            }
          }
        }
      });
      console.log('Bar chart created successfully');
    } catch (err) {
      console.error('Error creating bar chart:', err);
    }
  }

  renderDoughnutChart(): void {
    if (this.doughnutChart) {
      this.doughnutChart.destroy();
    }

    // Grab the <canvas> from ViewChild
    if (!this.doughnutChartCanvas) {
      console.error('Doughnut chart canvas ViewChild not found');
      return;
    }
    const canvas = this.doughnutChartCanvas.nativeElement;

    console.log('Doughnut chart canvas found, width/height:', canvas.width, canvas.height);

    try {
      const labels = this.topicScores.map(t => t.topic);
      const data = this.topicScores.map(t => t.score);

      // Generate dynamic colors
      const backgroundColors = this.generateColors(this.topicScores.length);

      this.doughnutChart = new Chart(canvas, {
        type: 'doughnut',
        data: {
          labels,
          datasets: [{
            data,
            backgroundColor: backgroundColors,
            borderColor: backgroundColors.map(color => color.replace('0.7', '1')),
            borderWidth: 1
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: 'right',
              labels: {
                color: '#ffffff',
                padding: 20,
                font: {
                  size: 12
                }
              }
            }
          }
        }
      });
      console.log('Doughnut chart created successfully');
    } catch (err) {
      console.error('Error creating doughnut chart:', err);
    }
  }

  // Simple function to return enough random colors
  generateColors(count: number): string[] {
    const baseColors = [
      'rgba(255, 184, 77, 0.7)', // your "primary" color
      'rgba(77, 166, 255, 0.7)',
      'rgba(255, 77, 77, 0.7)',
      'rgba(77, 255, 128, 0.7)',
      'rgba(191, 77, 255, 0.7)',
      'rgba(255, 255, 77, 0.7)',
    ];

    if (count <= baseColors.length) {
      return baseColors.slice(0, count);
    } else {
      const colors = [...baseColors];
      for (let i = baseColors.length; i < count; i++) {
        const r = Math.floor(Math.random() * 255);
        const g = Math.floor(Math.random() * 255);
        const b = Math.floor(Math.random() * 255);
        colors.push(`rgba(${r}, ${g}, ${b}, 0.7)`);
      }
      return colors;
    }
  }
}
