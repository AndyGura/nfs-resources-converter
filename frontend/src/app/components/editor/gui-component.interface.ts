import { EventEmitter } from '@angular/core';
import { BlockData, BlockSchema } from './types';

export interface GuiComponentInterface<BD extends BlockData = BlockData> {
  resourceId?: string;
  resourceName?: string;
  resourceSchema?: BlockSchema;
  resourceData?: BD;
  resourceDescription?: string;

  hideName?: boolean;
  hideBlockActions?: boolean;
  disabled?: boolean;

  changed: EventEmitter<BD | void>;
}
