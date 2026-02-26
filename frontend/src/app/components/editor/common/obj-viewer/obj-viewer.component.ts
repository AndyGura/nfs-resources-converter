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
import {
  Entity3d,
  FreeCameraController,
  Gg3dWorld,
  GgWorld,
  OrbitCameraController,
  Pnt3,
  Point2,
  Renderer3dEntity,
} from '@gg-web-engine/core';
import {
  ThreeDisplayObjectComponent,
  ThreeGgWorld,
  ThreeSceneComponent,
  ThreeVisualTypeDocRepo,
} from '@gg-web-engine/three';
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
import { ViewMode, ViewModeController } from '../../../../utils/three_editor/view-mode.controller';

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

// TODO use this from gg-web-engine after next release
type TypeDocOf<W extends GgWorld<any, any>> = W extends GgWorld<infer D, infer R, infer TypeDoc> ? TypeDoc : never;

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

  @Input() cameraControl: 'orbit' | 'free' = 'orbit';

  @Output() onObjectLoaded: EventEmitter<Object3D> = new EventEmitter<Object3D>();

  _paths$: BehaviorSubject<[string, string] | null> = new BehaviorSubject<[string, string] | null>(null);

  @ViewChild('previewCanvasContainer') previewCanvasContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('previewCanvas') previewCanvas!: ElementRef<HTMLCanvasElement>;

  private readonly destroyed$: Subject<void> = new Subject<void>();
  world!: ThreeGgWorld;
  renderer!: Renderer3dEntity<ThreeVisualTypeDocRepo>;
  entity: Entity3d<TypeDocOf<ThreeGgWorld>> | null = null;
  controller!: OrbitCameraController | FreeCameraController;

  meshes: Object3D[] = [];

  ambientLight: AmbientLight = new AmbientLight(0xffffff, 2);
  viewModeController?: ViewModeController;

  get viewMode(): ViewMode {
    return this.viewModeController?.viewMode || 'material';
  }

  constructor(private readonly cdr: ChangeDetectorRef) {
  }

  async ngAfterViewInit() {
    this.world = new Gg3dWorld({ visualScene: new ThreeSceneComponent() });
    await this.world.init();
    this.viewModeController = new ViewModeController(this.world.visualScene.nativeScene!, this.ambientLight);
    this.world.visualScene.nativeScene!.add(this.ambientLight);
    let rendererSize$: BehaviorSubject<Point2> = new BehaviorSubject<Point2>({ x: 1, y: 1 });
    this.renderer = this.world.addRenderer(
      this.world.visualScene.factory.createPerspectiveCamera({ frustrum: { near: 0.01, far: 10000 } }),
      this.previewCanvas.nativeElement,
      {
        size: rendererSize$.asObservable(),
        background: 0xaaaaaa,
      },
    );
    if (this.cameraControl === 'orbit') {
      this.controller = new OrbitCameraController(this.renderer, {
        mouseOptions: { canvas: this.previewCanvas.nativeElement },
        orbiting: { sensitivityX: 2, sensitivityY: 2 },
        orbitingElasticity: 30,
      });
    } else {
      this.controller = new FreeCameraController(this.world.keyboardInput, this.renderer, {
        mouseOptions: {
          canvas: this.previewCanvas.nativeElement,
          pointerLock: true,
        },
        keymap: 'wasd+arrows',
        cameraLinearSpeed: 40,
        cameraBoostMultiplier: 4,
        cameraMovementElasticity: 100,
        cameraRotationElasticity: 30,
        ignoreMouseUnlessPointerLocked: true,
        ignoreKeyboardUnlessPointerLocked: true,
      });
    }
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
        this.entity = new Entity3d<TypeDocOf<ThreeGgWorld>>({ object3D: new ThreeDisplayObjectComponent(object) });
        this.world.addEntity(this.entity);
        let bounds = { min: { x: -5, y: -5, z: -5 }, max: { x: 5, y: 5, z: 5 } };
        const calculatedBounds = this.entity.object3D!.getBoundings();
        if (!isNaN(calculatedBounds.min.x) && !isNaN(calculatedBounds.max.x)) {
          bounds = calculatedBounds;
        }
        const cameraTarget = Pnt3.scalarMult(Pnt3.add(bounds.min, bounds.max), 0.5);
        const cameraPosSpherical = { phi: 1.22, theta: -1.32, radius: Pnt3.dist(bounds.min, bounds.max) };
        if (this.controller instanceof OrbitCameraController) {
          this.controller.target = cameraTarget;
          this.controller.spherical = cameraPosSpherical;
        } else {
          // negate vector
          cameraPosSpherical.phi = Math.PI - cameraPosSpherical.phi;
          cameraPosSpherical.theta += Math.PI;
          this.renderer.position = Pnt3.sub(cameraTarget, Pnt3.fromSpherical(cameraPosSpherical));
          this.controller.spherical = cameraPosSpherical;
        }
        this.cdr.markForCheck();
      }
    });
  }

  public setViewMode(mode: ViewMode): void {
    this.viewModeController?.setViewMode(mode);
  }

  public toggleOnly(mesh: Object3D): void {
    for (const m of this.meshes) {
      m.visible = m === mesh;
      this.updateEdgeLineVisibility(m);
    }
  }

  public toRGB(color: Color | null): number {
    return ((color?.r || 0) << 16) | ((color?.g || 0) << 8) | (color?.b || 0);
  }

  ngOnDestroy(): void {
    this.viewModeController?.dispose();
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
