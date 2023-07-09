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

  private _resourceData: ReadData | null = null;
  get resourceData(): ReadData | null {
    return this._resourceData;
  }

  @Input()
  set resourceData(value: ReadData | null) {
    this._resourceData = value;
    if (this.editor) {
      this.editorProps.data = value ? new Uint8Array(value.value) : undefined;
      this.editor.$set({ props: { data: this.editorProps.data } });
      this.cdr.markForCheck();
    }
  }

  name: string = '';

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  private editor: any;
  private editorProps: HexEditorProps = {};

  constructor(private readonly cdr: ChangeDetectorRef) {}

  ngAfterViewInit(): void {
    if (this.resourceData) {
      this.editorProps.data = new Uint8Array(this.resourceData.value);
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
