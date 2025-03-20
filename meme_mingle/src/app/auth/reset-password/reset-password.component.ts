import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule, AbstractControl } from '@angular/forms';
import { ActivatedRoute, RouterModule, Router } from '@angular/router';
import { AppService } from '../../app.service';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterModule
  ],
  templateUrl: './reset-password.component.html',
  styleUrls: ['./reset-password.component.scss'],
})
export class ResetPasswordComponent implements OnInit {
  resetPasswordForm!: FormGroup;
  token: string = '';
  message: string = '';
  errorMessage: string = '';
  hidePassword: boolean = true;
  hideConfirmPassword: boolean = true;
  isSubmitting: boolean = false;

  constructor(
    private fb: FormBuilder,
    private route: ActivatedRoute,
    private authService: AppService,
    private router: Router
  ) {}

  ngOnInit() {
    // Get token from route params or query params
    this.token = this.route.snapshot.paramMap.get('token') || 
                this.route.snapshot.queryParams['token'] || '';
    
    if (!this.token) {
      this.errorMessage = 'Invalid or missing reset token. Please request a new password reset link.';
    }

    this.resetPasswordForm = this.fb.group({
      password: ['', [Validators.required, Validators.minLength(6)]],
      confirmPassword: ['', Validators.required]
    }, { validators: this.passwordsMatchValidator });
  }

  // Getter methods for form controls
  get password(): AbstractControl {
    return this.resetPasswordForm.get('password')!;
  }

  get confirmPassword(): AbstractControl {
    return this.resetPasswordForm.get('confirmPassword')!;
  }

  // Validator to check if passwords match
  passwordsMatchValidator(group: FormGroup) {
    const password = group.get('password')!.value;
    const confirmPassword = group.get('confirmPassword')!.value;
    return password === confirmPassword ? null : { passwordsMismatch: true };
  }

  // Toggle password visibility
  togglePasswordVisibility(): void {
    this.hidePassword = !this.hidePassword;
  }

  toggleConfirmPasswordVisibility(): void {
    this.hideConfirmPassword = !this.hideConfirmPassword;
  }

  // Get password strength
  getPasswordStrength(): string {
    const password = this.password.value;
    if (!password) return 'Weak';
    
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumbers = /\d/.test(password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    
    const strength = [hasUpperCase, hasLowerCase, hasNumbers, hasSpecialChar].filter(Boolean).length;
    
    if (password.length < 8) return 'Weak';
    if (strength <= 2) return 'Weak';
    if (strength === 3) return 'Medium';
    return 'Strong';
  }

  // Get password strength percentage for progress bar
  getPasswordStrengthPercent(): number {
    const password = this.password.value;
    if (!password) return 0;
    
    const hasUpperCase = /[A-Z]/.test(password);
    const hasLowerCase = /[a-z]/.test(password);
    const hasNumbers = /\d/.test(password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    
    let strength = 0;
    if (hasUpperCase) strength += 25;
    if (hasLowerCase) strength += 25;
    if (hasNumbers) strength += 25;
    if (hasSpecialChar) strength += 25;
    
    // Add length bonus
    if (password.length >= 6) strength += 10;
    if (password.length >= 8) strength += 15;
    
    // Cap at 100%
    return Math.min(100, strength);
  }

  // Get form progress
  getFormProgress(): number {
    let progress = 0;
    
    if (this.password.valid) progress += 50;
    if (this.confirmPassword.valid && !this.resetPasswordForm.hasError('passwordsMismatch')) progress += 50;
    
    return progress;
  }

  // Handle form submission
  onSubmit() {
    if (this.resetPasswordForm.invalid) {
      this.resetPasswordForm.markAllAsTouched();
      return;
    }

    this.isSubmitting = true;
    const newPassword = this.password.value;

    this.authService.resetPassword(this.token, newPassword).subscribe({
      next: (response: any) => {
        this.message = response.message || 'Password reset successfully! You will be redirected to the login page.';
        this.errorMessage = '';
        this.isSubmitting = false;
        
        // Redirect to login page after 3 seconds
        setTimeout(() => {
          this.router.navigate(['/auth/sign-in']);
        }, 3000);
      },
      error: (error: any) => {
        this.errorMessage = error.error?.message || 'Failed to reset password. Please try again or request a new reset link.';
        this.message = '';
        this.isSubmitting = false;
      }
    });
  }
}