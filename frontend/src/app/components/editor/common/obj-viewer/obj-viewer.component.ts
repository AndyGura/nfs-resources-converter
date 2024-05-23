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
import { BehaviorSubject, Subject, takeUntil } from 'rxjs';
import { Entity3d, Gg3dWorld, OrbitCameraController, Pnt3, Point2, Renderer3dEntity } from '@gg-web-engine/core';
import { ThreeDisplayObjectComponent, ThreeSceneComponent, ThreeVisualTypeDocRepo } from '@gg-web-engine/three';
import {
  AmbientLight,
  ClampToEdgeWrapping,
  Group,
  Material,
  Mesh,
  MeshBasicMaterial,
  NearestFilter,
  Object3D,
  Texture,
} from 'three';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader';
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader';
import { Color } from '@angular-material-components/color-picker';

export const setupNfs1Texture = (texture: Texture) => {
  texture.colorSpace = 'srgb';
  texture.anisotropy = 8;
  texture.magFilter = NearestFilter;
  texture.minFilter = NearestFilter;
};

type Control =
  | {
      label: string;
      type: 'checkbox';
      value: boolean;
      change: (value: boolean) => void;
    }
  | {
      label: string;
      type: 'radio';
      options: string[];
      value: string;
      change: (value: string) => void;
    }
  | {
      label: string;
      type: 'color';
      value: number;
      change: (value: number) => void;
    }
  | {
      label: string;
      type: 'slider';
      value: number;
      minValue: number;
      maxValue: number;
      valueStep: number;
      change: (value: number) => void;
    };

export type ObjViewerCustomControl = {
  title: string;
  controls: Control[];
};

@Component({
  selector: 'app-obj-viewer',
  templateUrl: './obj-viewer.component.html',
  styleUrls: ['./obj-viewer.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ObjViewerComponent implements AfterViewInit, OnDestroy {
  get paths(): [string, string] | null {
    return this._paths$.getValue();
  }

  @Input()
  set paths(value: [string, string] | null) {
    this._paths$.next(value);
  }

  @Input() visibilityControls: boolean = true;

  @Input() groupFunction: ((objectName: string) => string) | null = null;

  @Input() customControls: ObjViewerCustomControl[] = [];

  @Output() onObjectLoaded: EventEmitter<Object3D> = new EventEmitter<Object3D>();

  _paths$: BehaviorSubject<[string, string] | null> = new BehaviorSubject<[string, string] | null>(null);

  @ViewChild('previewCanvasContainer') previewCanvasContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('previewCanvas') previewCanvas!: ElementRef<HTMLCanvasElement>;

  private readonly destroyed$: Subject<void> = new Subject<void>();
  world!: Gg3dWorld<ThreeVisualTypeDocRepo, any, ThreeSceneComponent>;
  renderer!: Renderer3dEntity<ThreeVisualTypeDocRepo>;
  entity: Entity3d<ThreeVisualTypeDocRepo> | null = null;
  controller!: OrbitCameraController;

  meshes: Object3D[] = [];

  constructor(private readonly cdr: ChangeDetectorRef) {}

  async ngAfterViewInit() {
    this.world = new Gg3dWorld(new ThreeSceneComponent(), {
      init: async () => {},
      simulate: () => {},
    } as any);
    await this.world.init();
    this.world.visualScene.nativeScene!.add(new AmbientLight(0xffffff, 2));
    let rendererSize$: BehaviorSubject<Point2> = new BehaviorSubject<Point2>({ x: 1, y: 1 });
    this.renderer = this.world.addRenderer(
      this.world.visualScene.factory.createPerspectiveCamera({ frustrum: { near: 0.01, far: 10000 } }),
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

    this._paths$.pipe(takeUntil(this.destroyed$)).subscribe(async paths => {
      if (this.entity) {
        this.world.removeEntity(this.entity);
        this.entity.dispose();
        this.entity = null;
        this.meshes = [];
        this.cdr.markForCheck();
      }
      if (paths) {
        const [objPath, mtlPath] = paths;
        const objLoader = new OBJLoader();
        const mtlLoader = new MTLLoader();
        const mtl = await mtlLoader.loadAsync(mtlPath);
        mtl.preload();
        objLoader.setMaterials(mtl);
        const object = await objLoader.loadAsync(objPath);
        // merge to groups
        if (this.groupFunction) {
          const groups: { [prefix: string]: Object3D[] } = {};
          for (const c of object.children) {
            const groupId = this.groupFunction(c.name);
            if (!groups[groupId]) {
              groups[groupId] = [];
            }
            groups[groupId].push(c);
          }
          for (const groupId of Object.keys(groups)) {
            const g = new Group();
            g.add(...groups[groupId]);
            g.name = groupId;
            object.remove(...groups[groupId]);
            object.add(g);
          }
        }
        this.meshes = object.children;
        this.meshes.sort((a, b) => (a.name > b.name ? 1 : -1));
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
        this.onObjectLoaded.next(object);
        this.entity = new Entity3d<ThreeVisualTypeDocRepo>(new ThreeDisplayObjectComponent(object), null);
        this.world.addEntity(this.entity);
        let bounds = { min: { x: -5, y: -5, z: -5 }, max: { x: 5, y: 5, z: 5 } };
        const calculatedBounds = this.entity.object3D!.getBoundings();
        if (!isNaN(calculatedBounds.min.x) && !isNaN(calculatedBounds.max.x)) {
          bounds = calculatedBounds;
        }
        this.controller.target = Pnt3.scalarMult(Pnt3.add(bounds.min, bounds.max), 0.5);
        this.controller.radius = Pnt3.dist(bounds.min, bounds.max);
        this.controller.theta = -1.32;
        this.controller.phi = 1.22;
        this.cdr.markForCheck();
      }
    });
  }

  public toRGB(color: Color | null): number {
    return ((color?.r || 0) << 16) | ((color?.g || 0) << 8) | (color?.b || 0);
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
