import { EventEmitter } from '@angular/core';
import { BlockData, BlockSchema, Resource } from './types';

export interface GuiComponentInterface {
  resource: Resource | null;
  resourceDescription?: string;
  hideName?: boolean;
  hideBlockActions?: boolean;
  disabled?: boolean;

  changed: EventEmitter<void>;
}

export interface GuiComponentInterfaceNew<BD extends BlockData = BlockData> {
  resourceId: string;
  resourceName: string;
  resourceSchema: BlockSchema;
  resourceData: BD;
  resourceDescription?: string;

  hideName?: boolean;
  hideBlockActions?: boolean;
  disabled?: boolean;

  changed: EventEmitter<void>;
}
