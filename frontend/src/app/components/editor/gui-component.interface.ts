import { EventEmitter } from '@angular/core';
import { Resource } from './types';

export interface GuiComponentInterface {
  resource: Resource | null;
  resourceDescription?: string;
  hideBlockActions?: boolean;
  disabled?: boolean;

  changed: EventEmitter<void>;
}
