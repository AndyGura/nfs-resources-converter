import { EventEmitter } from '@angular/core';

export interface GuiComponentInterface {
  resource: Resource | null;
  resourceDescription?: string;

  changed: EventEmitter<void>;
}
