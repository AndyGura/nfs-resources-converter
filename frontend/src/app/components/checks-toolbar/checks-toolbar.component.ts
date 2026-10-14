import { ChangeDetectionStrategy, Component } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { MatBadgeModule } from '@angular/material/badge';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { ChecksService, GameCompatibility } from '../../services/checks.service';

const STATE_LABELS: { [state: string]: string } = {
  compatible: 'Compatible',
  not_compatible: 'Not compatible',
  unknown: 'Unknown: nothing in this file knows this game yet',
  loading: 'Checking...',
  error: 'The check failed',
};

// Top bar buttons: warnings of the opened file, and its compatibility with each game
@Component({
  selector: 'app-checks-toolbar',
  templateUrl: './checks-toolbar.component.html',
  styleUrls: ['./checks-toolbar.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    AsyncPipe,
    MatBadgeModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
  ],
})
export class ChecksToolbarComponent {
  constructor(readonly checks: ChecksService) {}

  // path of the block inside the file, '' for the file itself
  blockPath(id: string): string {
    const i = id.indexOf('__');
    return i === -1 ? '' : id.substring(i + 2);
  }

  // `field` -> <code>field</code>, the rest as plain text
  formatMessage(message: string): string {
    const escaped = (message || '').replace(
      /[&<>"']/g,
      c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]!,
    );
    return escaped.replace(/`([^`]+)`/g, '<code>$1</code>');
  }

  stateLabel(state: string): string {
    return STATE_LABELS[state] || state;
  }

  // why the game can't use the file
  problems(entry: GameCompatibility) {
    return entry.report?.problems || [];
  }
}
