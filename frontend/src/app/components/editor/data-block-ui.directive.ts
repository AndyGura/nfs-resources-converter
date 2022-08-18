import { Directive, ViewContainerRef } from '@angular/core';

@Directive({
  selector: '[dataBlockUI]'
})
export class DataBlockUIDirective {

  constructor(public viewContainerRef: ViewContainerRef) { }

}
