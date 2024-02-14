import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  EventEmitter,
  Input,
  OnDestroy,
  Output,
  ViewChild,
} from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';

declare var HexEditor: any;

enum NumberBase {
  Binary = 2,
  Octal = 8,
  Decimal = 10,
  Hexadecimal = 16,
}

interface HexEditorProps
  extends Partial<{
    data: ArrayBuffer;
    readonly: boolean;
    showHeader: boolean;
    showFooter: boolean;
    height: string;
    width: string;
    offsetBase: NumberBase;
    dataBase: NumberBase;
    bytesPerLine: number;
    start: number;
    end: number;
  }> {}

@Component({
  selector: 'app-binary-block-ui',
  templateUrl: './binary.block-ui.component.html',
  styleUrls: ['./binary.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BinaryBlockUiComponent implements GuiComponentInterface, AfterViewInit, OnDestroy {
  @ViewChild('editor') editorDiv?: ElementRef<HTMLDivElement>;

  private _resource: Resource | null = null;
  get resource(): Resource | null {
    return this._resource;
  }

  @Input()
  set resource(value: Resource | null) {
    this._resource = value;
    if (this.editor) {
      this.editorProps.data = value ? new Uint8Array(value.data) : undefined;
      this.editorProps.height = Math.min(24, Math.ceil((value?.data || []).length / 8) * 1.5) + 'rem';
      this.editor.$set({ props: this.editorProps });
      this.cdr.markForCheck();
    }
  }

  @Input()
  resourceDescription: string = '';

  @Input() disabled: boolean = false;

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  private editor: any;
  private editorProps: HexEditorProps = {
    showHeader: false,
    height: '10rem',
    readonly: false,
  };

  constructor(private readonly cdr: ChangeDetectorRef) {}

  ngAfterViewInit(): void {
    if (this.resource) {
      this.editorProps.data = new Uint8Array(this.resource.data);
      this.editorProps.height = Math.min(24, Math.ceil(this.resource.data.length / 8) * 1.5) + 'rem';
    }
    this.editor = new HexEditor({
      target: this.editorDiv?.nativeElement,
      props: this.editorProps,
    });
    this.cdr.markForCheck();
  }

  ngOnDestroy(): void {
    if (this.editor) {
      this.editor.$destroy();
    }
  }
}
