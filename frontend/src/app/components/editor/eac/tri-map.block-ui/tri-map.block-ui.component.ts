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
  ViewChild
} from '@angular/core';
import { GuiComponentInterface } from '../../gui-component.interface';
import { FreeCameraController, Gg3dEntity, Gg3dWorld, Pnt3, Point2, Qtrn } from '@gg-web-engine/core';
import { Gg3dObject, Gg3dVisualScene, GgRenderer } from '@gg-web-engine/three';
import { BehaviorSubject, debounceTime, filter, Subject, takeUntil } from 'rxjs';
import { EelDelegateService } from '../../../../services/eel-delegate.service';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader';
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader';
import { AmbientLight, ClampToEdgeWrapping, DoubleSide, Material, Mesh, MeshBasicMaterial } from 'three';
import { MainService } from '../../../../services/main.service';

@Component({
  selector: 'app-tri-map-block-ui',
  templateUrl: './tri-map.block-ui.component.html',
  styleUrls: ['./tri-map.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TriMapBlockUiComponent implements GuiComponentInterface, AfterViewInit, OnDestroy {

  @ViewChild('previewCanvasContainer') previewCanvasContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('previewCanvas') previewCanvas!: ElementRef<HTMLCanvasElement>;

  _resourceData$: BehaviorSubject<ReadData | null> = new BehaviorSubject<ReadData | null>(null);

  get resourceData(): ReadData | null {
    return this._resourceData$.getValue();
  };

  @Input() set resourceData(value: ReadData | null) {
    this._resourceData$.next(value);
  };

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  previewLoading$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(true);
  previewFamLocation$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);
  previewFamLoading$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);
  private previewMtlInstance: MTLLoader.MaterialCreator | null = null;
  private previewObjPath: string | undefined;

  name: string = '';
  world!: Gg3dWorld<Gg3dVisualScene, any>;
  renderer!: GgRenderer;
  entity: Gg3dEntity | null = null;
  controller!: FreeCameraController;

  private readonly destroyed$: Subject<void> = new Subject<void>();

  constructor(
    private readonly eelDelegate: EelDelegateService,
    private readonly cdr: ChangeDetectorRef,
    private readonly mainService: MainService,
  ) {
  }

  get previewFamPossibleLocations(): string[] {
    const blockId = this.resourceData?.block_id;
    if (blockId) {
      return [
        blockId.substring(0, blockId.indexOf('MISC')) + 'ETRACKFM' + blockId.substr(blockId.indexOf('MISC') + 4, 4) + '_001.FAM',
        blockId.substring(0, blockId.indexOf('MISC')) + 'GTRACKFM' + blockId.substr(blockId.indexOf('MISC') + 4, 4) + '_001.FAM',
        blockId.substring(0, blockId.indexOf('MISC')) + 'NTRACKFM' + blockId.substr(blockId.indexOf('MISC') + 4, 4) + '_M01.FAM',
        blockId.substring(0, blockId.indexOf('MISC')) + 'NTRACKFM' + blockId.substr(blockId.indexOf('MISC') + 4, 4) + '_R01.FAM',
        blockId.substring(0, blockId.indexOf('MISC')) + 'NTRACKFM' + blockId.substr(blockId.indexOf('MISC') + 4, 4) + '_T01.FAM',
      ]
    } else {
      return [];
    }
  }

  async ngAfterViewInit() {
    this.world = new Gg3dWorld(new Gg3dVisualScene(), {
      init: async () => {
      }, simulate: () => {
      }
    } as any);
    await this.world.init();
    this.world.visualScene.nativeScene!.add(new AmbientLight(0xffffff, 2));
    let rendererSize$: BehaviorSubject<Point2> = new BehaviorSubject<Point2>({ x: 1, y: 1 });
    this.renderer = new GgRenderer(
      this.previewCanvas.nativeElement,
      {
        size: rendererSize$.asObservable(),
        background: 0xaaaaaa,
      }
    );
    this.renderer.camera.position = { x: 0, y: 0, z: 2.5 };
    this.renderer.camera.rotation = Qtrn.lookAt(this.renderer.camera.position, Pnt3.add(this.renderer.camera.position, {
      x: 0,
      y: 1,
      z: 0
    }), { x: 0, y: 0, z: 1 });
    this.world.addEntity(this.renderer);

    this.controller = new FreeCameraController(this.world.keyboardInput, this.renderer.camera, {
      mouseOptions: {
        canvas: this.previewCanvas.nativeElement,
        pointerLock: true
      }, keymap: 'wasd+arrows', movementOptions: { speed: 1 }
    });
    this.world.addEntity(this.controller);
    const updateSize = () => {
      rendererSize$.next({
        x: this.previewCanvasContainer.nativeElement.clientWidth,
        y: this.previewCanvasContainer.nativeElement.clientHeight
      });
    }
    new ResizeObserver(updateSize).observe(this.previewCanvasContainer.nativeElement);
    updateSize();
    this.world.start();

    this._resourceData$.pipe(
      takeUntil(this.destroyed$),
    ).subscribe(async (data) => {
      this.previewLoading$.next(true);
      if (this.previewFamPossibleLocations[0]) {
        this.previewFamLocation$.next(this.previewFamPossibleLocations[0]);
        await this.onFamSelected(this.previewFamPossibleLocations[0]);
      }
      await this.loadPreviewObjPath(data?.block_id);
      await this.loadPreview();
      this.previewLoading$.next(false);
    });
    this.mainService.dataBlockChange$.pipe(
      takeUntil(this.destroyed$),
      filter(([blockId, _]) => !!this.resourceData && blockId.startsWith(this.resourceData!.block_id)),
      debounceTime(1500),
    ).subscribe(async () => {
      this.previewLoading$.next(true);
      await this.postTmpUpdates(this.resourceData?.block_id);
      await this.loadPreview();
      this.previewLoading$.next(false);
    });
  }

  async onFamSelected(path: string) {
    if (path == 'custom') {
      return;
    }
    this.previewFamLoading$.next(true);
    try {
      const files = await this.eelDelegate.serializeResource(path);
      const terrainTextures = files.filter(x => x.includes('.FAM/background') && x.endsWith('.png'));
      const mtl = terrainTextures.map(x => `newmtl ${x.substring(x.lastIndexOf('background') + 11, x.lastIndexOf('.png'))}
        Ka 1.000000 1.000000 1.000000
        Kd 1.000000 1.000000 1.000000
        Ks 0.000000 0.000000 0.000000
        illum 1
        Ns 0.000000
        map_Kd ${x}
`).join('\n');
      const mtlLoader = new MTLLoader();
      this.previewMtlInstance = await mtlLoader.parse(mtl, '');
      this.previewMtlInstance.preload();
    } finally {
      this.previewFamLoading$.next(false);
    }
    await this.loadPreview();
  }

  private async loadPreviewObjPath(blockId: string | undefined) {
    if (blockId) {
      const paths = await this.eelDelegate.serializeResource(blockId, {
        'geometry__save_obj': true,
        'geometry__save_blend': false,
        'geometry__export_to_gg_web_engine': false,
        'maps__save_as_chunked': false,
        'maps__save_collisions': false,
        'maps__save_spherical_skybox_texture': true,
      });
      this.previewObjPath = paths.find(x => x.endsWith('.obj'))!;
    } else {
      this.previewObjPath = undefined;
    }
  }

  private async loadPreview() {
    if (!this.previewObjPath) {
      return;
    }
    const objLoader = new OBJLoader();
    if (this.previewMtlInstance) {
      objLoader.setMaterials(this.previewMtlInstance);
    }
    const object = await objLoader.loadAsync(this.previewObjPath);
    object.traverse((x) => {
      if (x instanceof Mesh) {
        const materials: Material[] = x.material instanceof Array ? x.material : [x.material];
        for (const m of materials) {
          m.transparent = true;
          m.alphaTest = 0.5;
          if (m instanceof MeshBasicMaterial && m.map) {
            m.map.wrapS = ClampToEdgeWrapping;
            m.map.wrapT = ClampToEdgeWrapping;
            m.map.needsUpdate = true;
          }
          // FIXME remove workaround for normals
          m.side = DoubleSide;
        }
      }
    });
    this.unloadPreview();
    this.entity = new Gg3dEntity(new Gg3dObject(object), null);
    this.world.addEntity(this.entity);
    this.cdr.markForCheck();
  }

  private unloadPreview() {
    if (this.entity) {
      this.world.removeEntity(this.entity);
      this.entity.dispose();
      this.entity = null;
      this.cdr.markForCheck();
    }
  }

  private async postTmpUpdates(blockId: string | undefined) {
    if (blockId) {
      const paths = await this.eelDelegate.serializeResourceTmp(
        blockId,
        Object.entries(this.mainService.changedDataBlocks)
          .filter(([id, _]) => id != '__custom_action_performed__' && id.startsWith(blockId)).map(([id, value]) => {
          return { id, value };
        }),
        {
          'geometry__save_obj': true,
          'geometry__save_blend': false,
          'geometry__export_to_gg_web_engine': false,
          'maps__save_as_chunked': false,
          'maps__save_collisions': false,
          'maps__save_spherical_skybox_texture': true,
        });
      this.previewObjPath = paths.find(x => x.endsWith('.obj'))!;
    } else {
      this.previewObjPath = undefined;
    }
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
