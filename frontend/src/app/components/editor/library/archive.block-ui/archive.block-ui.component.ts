import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core';
import { BlockData, BlockSchema } from '../../types';
import { joinId } from '../../../../utils/join-id';
import { fileFormatIcon } from '../../../../utils/file-format-icon';
import { SubscribableGuiComponent } from '../../gui.component';
import { MatDialog } from '@angular/material/dialog';
import { ArchiveItemEditDialogComponent } from '../../common/archive-item-edit.dialog/archive-item-edit.dialog.component';
import { ArchiveDelegateItemTypeDialogComponent } from '../../common/archive-delegate-item-type.dialog/archive-delegate-item-type.dialog.component';
import { filter, firstValueFrom, Subject, takeUntil } from 'rxjs';
import { blockClassStr } from '../../../../utils/block_class_str';
import { MatSelectionList } from '@angular/material/list';
import { MatSnackBar } from '@angular/material/snack-bar';
import { isLazyStub } from '../../../../utils/lazy';

// an unloaded entry (`isLazyStub`) has `alias` only, until it is selected
type ArchiveChildData = {
  alias: string | null;
  item: BlockData;
  post_offset_payload: number[];
};

@Component({
  selector: 'app-archive-block-ui',
  templateUrl: './archive.block-ui.component.html',
  styleUrls: ['./archive.block-ui.component.scss'],
  host: { class: 'full-screen-editor' },
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class ArchiveBlockUiComponent extends SubscribableGuiComponent<{
  [key: string]: BlockData;
  children: ArchiveChildData[];
}> {
  childSchema: BlockSchema | undefined;
  supportsAliases: boolean = false;
  // the entries can be images (SHPI): image files can be added from disk
  canImportImages: boolean = false;
  isImporting: boolean = false;

  @ViewChild(MatSelectionList)
  private list!: MatSelectionList;

  override get resourceSchema(): BlockSchema | undefined {
    return super.resourceSchema;
  }

  override set resourceSchema(value: BlockSchema | undefined) {
    super.resourceSchema = value;
    this.childSchema = undefined;
    this.supportsAliases = false;
    this.canImportImages = false;
    if (value) {
      const childrenField = value.fields.find((x: { name: string; schema: BlockSchema }) => x.name === 'children');
      if (childrenField) {
        const childSchema = childrenField.schema.child_schema;
        this.supportsAliases = childSchema.fields.some((x: { name: string }) => x.name === 'alias');
        this.childSchema = childSchema.fields.find(
          (x: { name: string; schema: BlockSchema }) => x.name === 'item',
        )?.schema;
        this.canImportImages = (this.childSchema?.possible_resource_schemas || []).some((s: BlockSchema) =>
          s.block_class_mro.split('__').includes('EacImage'),
        );
      }
    }
  }

  override get resourceData(): { [key: string]: BlockData; children: ArchiveChildData[] } | undefined {
    return super.resourceData;
  }

  override set resourceData(value: { [key: string]: BlockData; children: ArchiveChildData[] } | undefined) {
    super.resourceData = value;
    this.updateSelectionOnDataChange();
  }

  private _selectedValue: [number, ArchiveChildData] | '___headers___' | null = null;

  get selectedValue(): [number, ArchiveChildData] | '___headers___' | null {
    return this._selectedValue;
  }

  set selectedValue(value: [number, ArchiveChildData] | '___headers___' | null) {
    this._selectedValue = value;
    if (value && value !== '___headers___' && isLazyStub(value[1])) {
      this.ensureChildLoaded(value[0]).then(() => {
        if (this._selectedValue === value) {
          this.cdr.markForCheck();
        }
      });
    }
  }

  // the entry is parsed by the backend on first use, its object is filled in place
  private ensureChildLoaded(index: number): Promise<void> {
    return this.mainService.ensureLoaded(
      joinId(this.resourceId!, `children/${index}`),
      this.resourceData!.children[index],
    );
  }

  isChildLoading(child: ArchiveChildData): boolean {
    return isLazyStub(child);
  }

  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly destroyed$ = new Subject<void>();

  constructor() {
    super();
    // a rename (edit dialog, backend) is notified to the most specific component only: the dialog
    this.changes.change$
      .pipe(
        takeUntil(this.destroyed$),
        filter(id => !!this.resourceId && id.startsWith(joinId(this.resourceId, 'children')) && id.endsWith('/alias')),
      )
      .subscribe(() => this.cdr.markForCheck());
  }

  override ngOnDestroy(): void {
    super.ngOnDestroy();
    this.destroyed$.next();
    this.destroyed$.complete();
  }

  // a free name for a new entry: new0, new1...
  private newAlias(): string {
    const taken = new Set((this.resourceData?.children || []).map(c => (c.alias || '').toLowerCase()));
    let n = 0;
    while (taken.has(`new${n}`)) n++;
    return `new${n}`;
  }

  override onExternalChanges() {
    super.onExternalChanges();
    this.updateSelectionOnDataChange();
  }

  private updateSelectionOnDataChange() {
    this.selectedValue = this.getSelectionAfterDataChange(this.selectedValue);
    this.cdr.markForCheck();
    // UI fix for mat list selection indicator
    if (this.selectedValue) {
      queueMicrotask(() => {
        if (this.selectedValue) {
          let listOpt = this.list.options.get(this.selectedValue === '___headers___' ? 0 : this.selectedValue![0] + 1);
          if (listOpt) {
            listOpt.selected = true;
          }
        }
      });
    }
  }

  private getSelectionAfterDataChange(
    lastSelectedValue: [number, ArchiveChildData] | '___headers___' | null,
  ): [number, ArchiveChildData] | '___headers___' | null {
    const value = super.resourceData;
    if (!value) return null;
    if (!lastSelectedValue) {
      if (value.children.length == 0) return '___headers___';
      return [0, value.children[0]];
    }
    if (lastSelectedValue === '___headers___') {
      return lastSelectedValue;
    }
    if (value.children.length > lastSelectedValue[0] && value.children[lastSelectedValue[0]] === lastSelectedValue[1]) {
      return lastSelectedValue;
    }
    for (const c of value.children) {
      if (
        c === lastSelectedValue[1] ||
        (lastSelectedValue[1].alias !== null &&
          lastSelectedValue[1].alias !== undefined &&
          c.alias === lastSelectedValue[1].alias)
      ) {
        return [value.children.indexOf(c), c];
      }
    }
    let index = Math.min(lastSelectedValue[0], value.children.length - 1);
    return [index, value.children[index]];
  }

  async addItem() {
    const id = joinId(this.resourceId!, 'children');
    let newItemKwargs = {};
    if (this.childSchema?.block_class_mro.includes('DelegateBlock__')) {
      const dialogRef = this.dialog.open(ArchiveDelegateItemTypeDialogComponent, {
        data: { schemas: this.childSchema.possible_resource_schemas },
      });
      const selection = await firstValueFrom(dialogRef.afterClosed());
      if (selection === undefined) {
        return;
      }
      newItemKwargs = { item: { choice_index: selection } };
    }
    const newItem = await this.mainService.getNewItemData(id, newItemKwargs);
    if (newItem === null) return;
    if (this.supportsAliases && !newItem.alias) {
      newItem.alias = this.newAlias();
    }
    this.emitNewChange({
      op: 'array_insert',
      id: id,
      index: this.resourceData!.children.length,
      value: newItem,
    });
  }

  // image files picked on disk become new 32-bit images at the end, as one undoable change
  async importImagesFromDisk() {
    const paths = await this.mainService.api.openFileDialog(true, [
      'Images (*.png;*.jpg;*.jpeg;*.bmp;*.gif;*.tga;*.webp;*.tif;*.tiff)',
      'All files (*.*)',
    ]);
    if (!paths || paths.length === 0) return;
    this.isImporting = true;
    this.cdr.markForCheck();
    try {
      const { items, skipped } = await this.mainService.api.newImagesFromFiles(this.resourceId!, paths);
      const id = joinId(this.resourceId!, 'children');
      const start = this.resourceData!.children.length;
      if (items.length > 0) {
        this.emitNewChange({
          op: 'bundle',
          changes: items.map((value, i) => ({
            op: 'array_insert',
            id,
            index: start + i,
            value,
            timestamp: Date.now(),
          })),
        });
        this.selectedValue = [start, this.resourceData!.children[start]];
        this.updateSelectionOnDataChange();
      }
      const added = `${items.length} image${items.length === 1 ? '' : 's'} added`;
      const skippedText = skipped.map(([name, reason]) => `${name} (${reason})`).join(', ');
      this.snackBar.open(skippedText ? `${added}. Skipped: ${skippedText}` : added, 'OK', { duration: 6000 });
    } finally {
      this.isImporting = false;
      this.cdr.markForCheck();
    }
  }

  async removeItem(index: number) {
    // the change keeps the removed entry for undo: it has to be the parsed one
    await this.ensureChildLoaded(index);
    this.emitNewChange({
      op: 'array_remove',
      id: joinId(this.resourceId!, 'children'),
      index,
      oldValue: this.resourceData!.children[index],
    });
  }

  moveItemUp(index: number) {
    this.emitNewChange({
      op: 'array_swap',
      id: joinId(this.resourceId!, 'children'),
      indexA: index,
      indexB: index - 1,
    });
  }

  moveItemDown(index: number) {
    this.emitNewChange({
      op: 'array_swap',
      id: joinId(this.resourceId!, 'children'),
      indexA: index,
      indexB: index + 1,
    });
  }

  async editItem(index: number) {
    await this.ensureChildLoaded(index);
    this.dialog.open(ArchiveItemEditDialogComponent, {
      data: {
        id: joinId(this.resourceId || '', `children/${index}`),
        data: this.resourceData!.children[index],
        schema: this.resourceSchema?.fields.find((x: { name: string; schema: BlockSchema }) => x.name === 'children')
          ?.schema.child_schema,
        name: this.resourceData!.children[index].alias || index.toString(),
      },
    });
  }

  childIcon(child: ArchiveChildData): string {
    let block_class_mro = '';
    if (this.childSchema) {
      if (this.childSchema.block_class_mro.includes('DelegateBlock__')) {
        // the kind of an unloaded entry is not known yet
        if (!child.item) return 'hourglass_empty';
        block_class_mro = this.childSchema.possible_resource_schemas[child.item.choice_index].block_class_mro;
      } else {
        block_class_mro = this.childSchema.block_class_mro;
      }
    }
    return fileFormatIcon(block_class_mro);
  }

  protected readonly joinId = joinId;
  protected readonly blockClassStr = blockClassStr;
}
