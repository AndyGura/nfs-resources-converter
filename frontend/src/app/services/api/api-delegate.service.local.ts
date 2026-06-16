import { Injectable, NgZone } from '@angular/core';
import { MatDialog } from '@angular/material/dialog';
import { ApiDelegateImplService } from './api-delegate-impl.service';
import { BaseApiDelegateService } from './base-api-delegate';

@Injectable()
export class ApiDelegateService extends BaseApiDelegateService {
  async initImpl() {
    return new ApiDelegateImplService(this.ngZone);
  }

  constructor(
    private readonly ngZone: NgZone,
    dialog: MatDialog,
  ) {
    super(dialog);
  }
}
