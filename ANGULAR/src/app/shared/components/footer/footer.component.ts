import { Component } from '@angular/core';

@Component({
  selector: 'app-footer',
  standalone: true,
  template: `
    <footer class="footer">
      <span class="footer__version">ГСТ АУРА v1.0.0</span>
      <span class="footer__copy">© 2026 "ГСТ"</span>
    </footer>
  `,
  styles: [`
    .footer {
      height: var(--footer-height);
      background: var(--color-bg-2);
      border-top: 1px solid var(--color-border);
      padding: 0 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      flex-shrink: 0;
    }
    .footer__version, .footer__copy {
      color: var(--color-text-3);
      font-size: 11px;
    }
  `],
})
export class FooterComponent {}
