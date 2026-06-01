import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'chat', pathMatch: 'full' },
  {
    path: 'login',
    loadComponent: () =>
      import('./features/auth/components/login/login.component')
        .then(m => m.LoginComponent),
    title: 'Вход — КАИ',
  },
  {
    path: 'chat',
    loadComponent: () =>
      import('./features/chat/components/chat-window/chat-window.component')
        .then(m => m.ChatWindowComponent),
    canActivate: [authGuard],
    title: 'Чат — КАИ',
  },
  { path: '**', redirectTo: 'chat' },
];
