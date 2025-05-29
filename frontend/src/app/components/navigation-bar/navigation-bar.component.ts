import { AfterViewInit, ChangeDetectionStrategy, Component } from '@angular/core';
import { MatDividerModule } from '@angular/material/divider';
import { MatButtonModule } from '@angular/material/button';
import { AsyncPipe, NgFor, NgIf } from '@angular/common';
import { NavigationService } from '../../services/navigation.service';
import { BehaviorSubject } from 'rxjs';
import { MainService } from '../../services/main.service';

@Component({
  selector: 'app-navigation-bar',
  template: `
    <nav class="flex items-center space-x-1 py-2 px-4 bg-surface shadow-sm rounded-md">
      <button mat-button (click)="navigate(0)" class="font-medium text-primary">
        {{ rootName$ | async }}
      </button>

      <ng-container *ngFor="let item of (navigation.navigationPath$ | async) || []; let i = index">
        <ng-container *ngIf="!['data', 'children'].includes(item)">
          <mat-divider vertical></mat-divider>
          <span>/</span>
          <button mat-button (click)="navigate(i + 1)" class="font-medium text-secondary">
            {{ item }}
          </button>
        </ng-container>
      </ng-container>
    </nav>
  `,
  styles: [
    `
      :host {
        padding: 1rem;
        padding-bottom: 0;
      }

      nav {
        display: flex;
        align-items: center;
        background-color: var(--mat-background);
        border-radius: 4px;
      }

      button {
        text-transform: none;
      }
    `,
  ],
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatButtonModule, MatDividerModule, NgFor, NgIf, AsyncPipe],
})
export class NavigationBarComponent implements AfterViewInit {
  public readonly rootName$: BehaviorSubject<string> = new BehaviorSubject<string>('/');

  constructor(public readonly navigation: NavigationService, public readonly main: MainService) {}

  ngAfterViewInit(): void {
    this.main.resource$.subscribe(r => {
      let rootBlockId = r?.id;
      if (!rootBlockId) {
        this.rootName$.next('/');
      } else {
        const name = rootBlockId.substring(rootBlockId.lastIndexOf('/') + 1);
        this.rootName$.next(name);
      }
    });
  }

  navigate(index: number): void {
    this.navigation.navigateBack(this.navigation.navigationPath$.value.length - index);
  }
}
