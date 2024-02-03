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
import { Entity3d, Gg3dWorld, OrbitCameraController, Pnt3, Point2, Renderer3dEntity } from '@gg-web-engine/core';
import { BehaviorSubject, debounceTime, filter, Subject, takeUntil } from 'rxjs';
import { EelDelegateService } from '../../../../services/eel-delegate.service';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader';
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader';
import {
  AmbientLight,
  ClampToEdgeWrapping,
  Material,
  Mesh,
  MeshBasicMaterial,
  NearestFilter,
  sRGBEncoding,
  Texture,
} from 'three';
import { MainService } from '../../../../services/main.service';
import { ThreeDisplayObjectComponent, ThreeSceneComponent, ThreeVisualTypeDocRepo } from '@gg-web-engine/three';

export const setupNfs1Texture = (texture: Texture) => {
  texture.encoding = sRGBEncoding;
  texture.anisotropy = 8;
  texture.magFilter = NearestFilter;
  texture.minFilter = NearestFilter;
};

@Component({
  selector: 'app-orip-geometry-block-ui',
  templateUrl: './orip-geometry.block-ui.component.html',
  styleUrls: ['./orip-geometry.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class OripGeometryBlockUiComponent implements GuiComponentInterface, AfterViewInit, OnDestroy {
  get resource(): Resource | null {
    return this._resource$.getValue();
  }

  @Input()
  set resource(value: Resource | null) {
    this._resource$.next(value);
  }

  _resource$: BehaviorSubject<Resource | null> = new BehaviorSubject<Resource | null>(null);

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  @ViewChild('previewCanvasContainer') previewCanvasContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('previewCanvas') previewCanvas!: ElementRef<HTMLCanvasElement>;

  private readonly destroyed$: Subject<void> = new Subject<void>();
  world!: Gg3dWorld<ThreeVisualTypeDocRepo, any, ThreeSceneComponent>;
  renderer!: Renderer3dEntity<ThreeVisualTypeDocRepo>;
  entity: Entity3d<ThreeVisualTypeDocRepo> | null = null;
  controller!: OrbitCameraController;

  constructor(
    private readonly eelDelegate: EelDelegateService,
    private readonly cdr: ChangeDetectorRef,
    private readonly mainService: MainService,
  ) {}

  async ngAfterViewInit() {
    this.world = new Gg3dWorld(new ThreeSceneComponent(), {
      init: async () => {},
      simulate: () => {},
    } as any);
    await this.world.init();
    this.world.visualScene.nativeScene!.add(new AmbientLight(0xffffff, 2));
    let rendererSize$: BehaviorSubject<Point2> = new BehaviorSubject<Point2>({ x: 1, y: 1 });
    this.renderer = this.world.addRenderer(
      this.world.visualScene.factory.createPerspectiveCamera(),
      this.previewCanvas.nativeElement,
      {
        size: rendererSize$.asObservable(),
        background: 0xaaaaaa,
      },
    );
    this.controller = new OrbitCameraController(this.renderer, {
      mouseOptions: { canvas: this.previewCanvas.nativeElement },
    });
    this.world.addEntity(this.controller);
    const updateSize = () => {
      rendererSize$.next({
        x: this.previewCanvasContainer.nativeElement.clientWidth,
        y: this.previewCanvasContainer.nativeElement.clientHeight,
      });
    };
    new ResizeObserver(updateSize).observe(this.previewCanvasContainer.nativeElement);
    updateSize();
    this.world.start();

    this._resource$.pipe(takeUntil(this.destroyed$)).subscribe(async res => {
      const paths = await this.loadPreviewFilePaths(res?.id);
      if (paths) {
        await this.loadPreview(paths);
      }
    });
    this.mainService.dataBlockChange$
      .pipe(
        takeUntil(this.destroyed$),
        filter(([blockId, _]) => !!this.resource && blockId.startsWith(this.resource!.id)),
        debounceTime(1500),
      )
      .subscribe(async () => {
        this.unloadPreview();
        const paths = await this.postTmpUpdates(this.resource?.id);
        if (paths) {
          await this.loadPreview(paths);
        }
      });
  }

  private async postTmpUpdates(blockId: string | undefined): Promise<[string, string] | undefined> {
    if (blockId) {
      const paths = await this.eelDelegate.serializeResourceTmp(
        blockId,
        Object.entries(this.mainService.changedDataBlocks)
          .filter(([id, _]) => id != '__has_external_changes__' && id.startsWith(blockId))
          .map(([id, value]) => {
            return { id, value };
          }),
        {
          geometry__save_obj: true,
          geometry__save_blend: false,
          geometry__export_to_gg_web_engine: false,
          geometry__replace_car_wheel_with_dummies: false,
        },
      );
      const objPath = paths.find(x => x.endsWith('.obj'))!;
      const mtlPath = paths.find(x => x.endsWith('.mtl'))!;
      return [objPath, mtlPath];
    }
    return;
  }

  private async loadPreviewFilePaths(blockId: string | undefined): Promise<[string, string] | undefined> {
    if (blockId) {
      const paths = await this.eelDelegate.serializeResource(blockId, {
        geometry__save_obj: true,
        geometry__save_blend: false,
        geometry__export_to_gg_web_engine: false,
        geometry__replace_car_wheel_with_dummies: false,
      });
      const objPath = paths.find(x => x.endsWith('.obj'))!;
      const mtlPath = paths.find(x => x.endsWith('.mtl'))!;
      return [objPath, mtlPath];
    }
    return;
  }

  private async loadPreview([objPath, mtlPath]: [string, string]) {
    this.unloadPreview();
    const objLoader = new OBJLoader();
    const mtlLoader = new MTLLoader();
    const mtl = await mtlLoader.loadAsync(mtlPath);
    mtl.preload();
    objLoader.setMaterials(mtl);
    const object = await objLoader.loadAsync(objPath);
    object.traverse(x => {
      if (x instanceof Mesh) {
        const materials: Material[] = x.material instanceof Array ? x.material : [x.material];
        for (const m of materials) {
          m.transparent = true;
          m.alphaTest = 0.5;
          if (m instanceof MeshBasicMaterial && m.map) {
            m.map.wrapS = ClampToEdgeWrapping;
            m.map.wrapT = ClampToEdgeWrapping;
            setupNfs1Texture(m.map);
            m.map.needsUpdate = true;
          }
        }
      }
    });
    this.entity = new Entity3d<ThreeVisualTypeDocRepo>(new ThreeDisplayObjectComponent(object), null);
    this.world.addEntity(this.entity);

    const bounds = this.entity.object3D!.getBoundings();
    this.controller.target = Pnt3.scalarMult(Pnt3.add(bounds.min, bounds.max), 0.5);
    this.controller.radius = Pnt3.dist(bounds.min, bounds.max);
    this.controller.theta = -1.32;
    this.controller.phi = 1.22;
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

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
