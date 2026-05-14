import { Injectable, NgZone } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { BaseApiDelegateService } from './base-api-delegate';

@Injectable()
export class ApiDelegateService extends BaseApiDelegateService {
  async initImpl() {
    return import(/* webpackChunkName: "eel" */ './api-delegate-impl.service').then(
      m => new m.ApiDelegateImplService(this.ngZone),
    );
  }

  constructor(private readonly ngZone: NgZone, dialog: MatDialog) {
    super(dialog);
  }
}
