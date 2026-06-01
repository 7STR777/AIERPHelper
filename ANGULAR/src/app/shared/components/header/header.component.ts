import { Component, inject, input, output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ThemeService } from '../../../core/services/theme.service';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './header.component.html',
  styleUrls: ['./header.component.scss'],
})
export class HeaderComponent {
  private readonly themeService = inject(ThemeService);

  userName = input<string>('Иванов И. И.');
  logout = output<void>();

  readonly theme = this.themeService.theme;

  toggleTheme(): void {
    this.themeService.toggle();
  }

  onLogout(): void {
    this.logout.emit();
  }
}
