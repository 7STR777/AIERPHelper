import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, delay, of } from 'rxjs';
import { environment } from '@env/environment';

// ============================================================
// CHAT API — подключение к реальному бэкенду
//
// Эндпоинт: POST /chat
// Заголовок: Authorization: Bearer <token>  ← добавляет interceptor автоматически
//
// Запрос:  { "query": "Что такое ДСЕ?" }
// Ответ:   { "messageID": "abc123...", "content": "...", "timestamp": "2026-..." }
//
// Mock отключается автоматически в production-сборке (Docker).
// ============================================================

const USE_MOCK = !environment.production;

export interface ChatRequest  { query: string; }
export interface ChatResponse {
  messageID: string;   // GUID без дефисов
  content:   string;   // текст ответа
  timestamp: string;   // ISO 8601 UTC
}

export interface RatingPayload {
  question: string;
  answer:   string;
  rating:   'good' | 'bad';
}

@Injectable({ providedIn: 'root' })
export class ChatApiService {
  private readonly http = inject(HttpClient);

  ask(query: string): Observable<ChatResponse> {
    if (USE_MOCK) return this.mockResponse(query);
    // Токен добавляется автоматически через authInterceptor
    return this.http.post<ChatResponse>(`${environment.apiUrl}/chat`, { query });
  }

  /** Оценка ответа — плохие отправляются в поддержку */
  submitRating(payload: RatingPayload): Observable<void> {
    if (USE_MOCK) {
      if (payload.rating === 'bad') {
        const stored = JSON.parse(localStorage.getItem('bad_ratings') ?? '[]');
        stored.push({ ...payload, timestamp: new Date().toISOString() });
        localStorage.setItem('bad_ratings', JSON.stringify(stored));
        console.log('[MOCK] Bad rating saved locally:', payload.question);
      }
      return of(undefined).pipe(delay(200));
    }
    // TODO: уточнить у бэкендера — планирует ли он добавить POST /feedback ?
    // Пока плохие ответы уже попадают в dbo.RagSupportRequests автоматически
    // когда контент содержит "обратитесь в техподдержку"
    return of(undefined);
  }

  // ── MOCK ────────────────────────────────────────────────
  private mockResponse(query: string): Observable<ChatResponse> {
    const answers: Record<string, string> = {
      'заказ':  'Для создания производственного заказа перейдите в «Производство → Заказы», нажмите «Создать» и заполните номенклатуру, количество и дату выпуска.',
      'склад':  'Складской учёт ведётся в разделе «Склад → Движение товаров». Все операции приходуются автоматически при проведении документов.',
      'отчёт':  'Отчёты формируются в разделе «Аналитика». Выберите тип, укажите период и нажмите «Сформировать».',
      'период': 'Закрытие периода выполняется в «Финансы → Закрытие периода». Убедитесь что все документы проведены.',
      'права':  'Управление правами находится в «Администрирование → Пользователи и права». Требуется роль Администратора.',
      'дсе':    'ДСЕ (Деталь Сборочная Единица) — базовый объект номенклатуры в ERP. Создаётся в «Номенклатура → ДСЕ».',
    };
    const lower = query.toLowerCase();
    let content = 'Нет информации в базе по данному вопросу. Пожалуйста, обратитесь в техподдержку.';
    for (const [key, val] of Object.entries(answers)) {
      if (lower.includes(key)) { content = val; break; }
    }
    return of({
      messageID: crypto.randomUUID().replace(/-/g, ''),
      content,
      timestamp: new Date().toISOString(),
    }).pipe(delay(900 + Math.random() * 600));
  }
}
