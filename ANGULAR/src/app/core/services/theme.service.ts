import { Injectable, inject, signal, effect } from '@angular/core';
import { AuthService } from './auth.service';

export type Theme = 'dark' | 'light';

const GLOBAL_THEME_KEY = 'gst_kai_theme';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  private readonly auth = inject(AuthService);

  readonly theme = signal<Theme>(this.loadGlobal());

  constructor() {
    effect(() => {
      const login = this.auth.user()?.login;
      this.theme.set(login ? this.loadForUser(login) : this.loadGlobal());
    }, { allowSignalWrites: true });

    effect(() => {
      const theme = this.theme();
      document.documentElement.setAttribute('data-theme', theme);

      const login = this.auth.user()?.login;
      if (login) {
        localStorage.setItem(this.userKey(login), theme);
      } else {
        localStorage.setItem(GLOBAL_THEME_KEY, theme);
      }
    });
  }

  toggle(): void {
    this.theme.update(t => (t === 'dark' ? 'light' : 'dark'));
  }

  setTheme(theme: Theme): void {
    this.theme.set(theme);
  }

  private userKey(login: string): string {
    return `gst_kai_theme_${login}`;
  }

  private loadForUser(login: string): Theme {
    const stored = localStorage.getItem(this.userKey(login));
    return stored === 'light' || stored === 'dark' ? stored : this.loadGlobal();
  }

  private loadGlobal(): Theme {
    const stored = localStorage.getItem(GLOBAL_THEME_KEY);
    return stored === 'light' ? 'light' : 'dark';
  }
}
