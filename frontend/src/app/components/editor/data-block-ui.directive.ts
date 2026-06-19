import { Directive, ViewContainerRef } from '@angular/core';

@Directive({
  selector: '[dataBlockUI]',
  standalone: false,
})
export class DataBlockUIDirective {
  constructor(public viewContainerRef: ViewContainerRef) {}
}
