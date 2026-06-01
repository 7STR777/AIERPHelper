import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { AuthService } from '@core/services/auth.service';
import { ThemeService } from '@core/services/theme.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, CommonModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent {
  private readonly auth   = inject(AuthService);
  private readonly router = inject(Router);
  private readonly themeService = inject(ThemeService);

  readonly theme = this.themeService.theme;

  login    = '';
  password = '';
  showPassword = false;
  error    = signal('');
  loading  = signal(false);

  toggleTheme(): void {
    this.themeService.toggle();
  }

  onSubmit(): void {
    this.error.set('');
    if (!this.login.trim() || !this.password.trim()) {
      this.error.set('Заполните все поля');
      return;
    }
    this.loading.set(true);
    try {
      this.auth.login(this.login.trim(), this.password).subscribe({
        next: () => {
          this.loading.set(false);
          this.router.navigate(['/chat']);
        },
        error: () => {
          this.loading.set(false);
          this.error.set('Неверный логин или пароль');
        },
      });
    } catch {
      this.loading.set(false);
      this.error.set('Неверный логин или пароль');
    }
  }
}
