import { ChangeDetectionStrategy, Component, inject, ViewChild } from '@angular/core';
import { NavigationService } from '../../../../services/navigation.service';
import { BlockData, BlockSchema } from '../../types';
import { joinId } from '../../../../utils/join-id';
import { fileFormatIcon } from '../../../../utils/file-format-icon';
import { SubscribableGuiComponent } from '../../gui.component';
import { MatDialog } from '@angular/material/dialog';
import { ArchiveItemEditDialogComponent } from '../../common/archive-item-edit.dialog/archive-item-edit.dialog.component';
import { ArchiveDelegateItemTypeDialogComponent } from '../../common/archive-delegate-item-type.dialog/archive-delegate-item-type.dialog.component';
import { firstValueFrom } from 'rxjs';
import { blockClassStr } from '../../../../utils/block_class_str';
import { MatSelectionList } from '@angular/material/list';

type ArchiveChildData = {
  alias: string | null;
  item: BlockData;
  pre_offset_payload: number[];
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

  @ViewChild(MatSelectionList)
  private list!: MatSelectionList;

  override get resourceSchema(): BlockSchema | undefined {
    return super.resourceSchema;
  }

  override set resourceSchema(value: BlockSchema | undefined) {
    super.resourceSchema = value;
    this.childSchema = undefined;
    this.supportsAliases = false;
    if (value) {
      const childrenField = value.fields.find((x: { name: string; schema: BlockSchema }) => x.name === 'children');
      if (childrenField) {
        const childSchema = childrenField.schema.child_schema;
        this.supportsAliases = childSchema.fields.some((x: { name: string }) => x.name === 'alias');
        this.childSchema = childSchema.fields.find(
          (x: { name: string; schema: BlockSchema }) => x.name === 'item',
        )?.schema;
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

  selectedValue: [number, ArchiveChildData] | '___headers___' | null = null;

  private readonly navigation = inject(NavigationService);
  private readonly dialog = inject(MatDialog);

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

  onDoubleClick(childIndex: number) {
    this.navigation.navigateToId(joinId(this.resourceId || '', `children/${childIndex}/item`));
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
    this.emitNewChange({
      op: 'array_insert',
      id: id,
      index: this.resourceData!.children.length,
      value: newItem,
    });
  }

  removeItem(index: number) {
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

  editItem(index: number) {
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
