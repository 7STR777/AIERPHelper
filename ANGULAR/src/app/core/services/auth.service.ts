import { Injectable, inject, signal, computed } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap, of, delay } from 'rxjs';
import { environment } from '@env/environment';

// ============================================================
// СЕРВИС АВТОРИЗАЦИИ
//
// POST /login  →  { "login": "user", "password": "user123" }
// Ответ:          { "token": "eyJ..." }
//
// Токен сохраняется в sessionStorage и добавляется к каждому
// запросу через HttpInterceptor (error.interceptor.ts).
//
// Mock отключается автоматически в production-сборке (Docker).
// ============================================================

const USE_MOCK = !environment.production;

export interface LoginRequest  { login: string; password: string; }
export interface LoginResponse { token: string; }

export interface AuthUser {
  login: string;
  fullName: string; // для отображения в хедере
}

const TOKEN_KEY = 'gst_kai_token';
const USER_KEY  = 'gst_kai_user';

// Демо-пользователи из README бэкендера
const MOCK_USERS = [
  { login: 'user',  password: 'user123',  fullName: 'Пользователь' },
  { login: 'admin', password: 'admin123', fullName: 'Администратор' },
];

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);

  private readonly _user  = signal<AuthUser | null>(this.loadUser());
  private readonly _token = signal<string | null>(sessionStorage.getItem(TOKEN_KEY));

  readonly user       = this._user.asReadonly();
  readonly isLoggedIn = computed(() => this._token() !== null);

  /** Получить токен для подстановки в заголовок */
  getToken(): string | null { return this._token(); }

  login(login: string, password: string): Observable<LoginResponse> {
    if (USE_MOCK) {
      const found = MOCK_USERS.find(u => u.login === login && u.password === password);
      if (found) {
        const fakeToken = 'mock_token_' + btoa(login + ':' + Date.now());
        const resp: LoginResponse = { token: fakeToken };
        this.saveSession(resp.token, { login: found.login, fullName: found.fullName });
        return of(resp).pipe(delay(400));
      }
      // Симулируем 401
      throw new Error('Неверный логин или пароль');
    }

    return this.http
      .post<LoginResponse>(`${environment.apiUrl}/login`, { login, password })
      .pipe(tap(resp => {
        // Декодируем имя из JWT если нужно, пока используем логин
        this.saveSession(resp.token, { login, fullName: login });
      }));
  }

  logout(): void {
    this._token.set(null);
    this._user.set(null);
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
  }

  private saveSession(token: string, user: AuthUser): void {
    this._token.set(token);
    this._user.set(user);
    sessionStorage.setItem(TOKEN_KEY, token);
    sessionStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  private loadUser(): AuthUser | null {
    try {
      const raw = sessionStorage.getItem(USER_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch { return null; }
  }
}
