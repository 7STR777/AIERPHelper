import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

// ============================================================
// HTTP INTERCEPTOR
// 1. Автоматически добавляет JWT-токен к каждому запросу.
// 2. При 401 — разлогинивает и отправляет на /login.
// ============================================================

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth   = inject(AuthService);
  const router = inject(Router);

  const token = auth.getToken();
  if (token) {
    req = req.clone({
      setHeaders: { Authorization: `Bearer ${token}` }
    });
  }

  return next(req).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status === 401) {
        auth.logout();
        router.navigate(['/login']);
      }
      let message = 'Ошибка сервера';
      if (error.status === 0)   message = 'Нет соединения с сервером';
      if (error.status === 403) message = 'Доступ запрещён';
      if (error.status === 404) message = 'Ресурс не найден';
      if (error.status >= 500)  message = 'Ошибка на стороне сервера';
      console.error(`[HTTP ${error.status}]`, message, error);
      return throwError(() => new Error(message));
    })
  );
};
