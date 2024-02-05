import { EventEmitter } from '@angular/core';

export interface GuiComponentInterface {
  resource: Resource | null;
  resourceDescription?: string;
  hideBlockActions?: boolean;

  changed: EventEmitter<void>;
}
