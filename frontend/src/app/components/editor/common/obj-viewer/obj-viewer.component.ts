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
  Box3,
  ClampToEdgeWrapping,
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
import { ViewMode, ViewModeController } from './view-mode-toolbar/view-mode.controller';

export type ViewFilterOpts = {
  name: string;
  filterGroups: string[];
  checkedIndex: number;
  pickFunction: (object: Object3D) => number;
}

class ViewFilter {

  private _meshes: Object3D[] = [];

  get opts(): ViewFilterOpts {
    return this._opts;
  }

  set opts(value: ViewFilterOpts) {
    this._opts = value;
  }

  set meshes(meshes: Object3D[]) {
    this._meshes = meshes;
    this.selectFirstNonEmptyGroup();
  }

  constructor(private _opts: ViewFilterOpts) {
  }

  isGroupEmpty(group: string): boolean {
    const groupIndex = this._opts.filterGroups.indexOf(group);
    for (const m of this._meshes) {
      if (this._opts.pickFunction(m) === groupIndex) {
        return false;
      }
    }
    return true;
  }

  listSelectedGroupMeshes(): Object3D[] {
    return this._meshes.filter(m => this._opts.pickFunction(m) === this._opts.checkedIndex);
  }

  selectFirstNonEmptyGroup(): void {
    for (let i = 0; i < this._opts.filterGroups.length; i++) {
      if (!this.isGroupEmpty(this._opts.filterGroups[i])) {
        this._opts.checkedIndex = i;
        return;
      }
    }
    this._opts.checkedIndex = 0;
  }

}

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

// TODO move to a different place
export const setupNfs1Texture = (texture: Texture) => {
  texture.colorSpace = 'srgb';
  texture.anisotropy = 8;
  texture.magFilter = NearestFilter;
  texture.minFilter = NearestFilter;
};

@Component({
  selector: 'app-obj-viewer',
  templateUrl: './obj-viewer.component.html',
  styleUrls: ['./obj-viewer.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ObjViewerComponent implements AfterViewInit, OnDestroy {

  private _cameraControl: 'orbit' | 'free' = 'orbit';
  get cameraControl(): 'orbit' | 'free' {
    return this._cameraControl;
  }

  @Input()
  /// camera: orbit or free-fly
  set cameraControl(value: 'orbit' | 'free') {
    if (this._cameraControl === value) return;
    this._cameraControl = value;
    if (this.controller) {
      this.setupCameraController();
    }
  }

  @Input()
  //// use filters to visually switch between sets of meshes
  set viewFilters(value: ViewFilterOpts[]) {
    this._viewFilters = value.map(v => new ViewFilter(v));
    for (const f of this._viewFilters) {
      f.meshes = this.meshes;
    }
    this.applyViewFilters();
  }

  _viewFilters: ViewFilter[] = [];

  /// show meshes list in the menu
  @Input() visibilityControls: boolean = true;

  private _visibilityGroupFunction: ((object: Object3D) => string) | null = null;
  @Input()
  /// group meshes in the visibility menu
  set visibilityGroupFunction(value: ((object: Object3D) => string) | null) {
    this._visibilityGroupFunction = value;
    this.rebuildUiGroups();
  }

  @Input() customControls: ObjViewerCustomControl[] = [];

  _paths$: BehaviorSubject<[string, string] | null> = new BehaviorSubject<[string, string] | null>(null);

  get paths(): [string, string] | null {
    return this._paths$.getValue();
  }

  @Input()
  set paths(value: [string, string] | null) {
    this._paths$.next(value);
  }

  @Output() onObjectLoaded: EventEmitter<Object3D> = new EventEmitter<Object3D>();

  @ViewChild('previewCanvasContainer') previewCanvasContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('previewCanvas') previewCanvas!: ElementRef<HTMLCanvasElement>;

  private readonly destroyed$: Subject<void> = new Subject<void>();
  world!: ThreeGgWorld;
  renderer!: Renderer3dEntity<ThreeVisualTypeDocRepo>;
  entity: Entity3d<TypeDocOf<ThreeGgWorld>> | null = null;
  controller!: OrbitCameraController | FreeCameraController;

  meshes: Object3D[] = [];
  displayMeshes: Object3D[] = [];
  uiGroups: { [prefix: string]: { visible: boolean, meshes: Object3D[] } } | null = null;

  ambientLight: AmbientLight = new AmbientLight(0xffffff, 2);
  viewModeController?: ViewModeController;
  private isFirstFrame = true;

  get viewMode(): ViewMode {
    return this.viewModeController?.viewMode || 'material';
  }

  constructor(private readonly cdr: ChangeDetectorRef) {
  }

  private setupCameraController() {
    if (this.controller) {
      this.world.removeEntity(this.controller);
      this.controller.dispose();
    }
    if (this._cameraControl === 'orbit') {
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
        cameraLinearSpeed: 50,
        cameraBoostMultiplier: 8,
        cameraMovementElasticity: 100,
        cameraRotationElasticity: 30,
        ignoreMouseUnlessPointerLocked: true,
        ignoreKeyboardUnlessPointerLocked: true,
      });
    }
    this.world.addEntity(this.controller);
    if (this._cameraControl === 'orbit') {
      this.controller.spherical = { phi: 1.22, theta: -1.32, radius: 10 };
    } else {
      this.controller.spherical = { phi: Math.PI - 1.22, theta: -1.32 + Math.PI, radius: 1 };
    }
    this.renderer.position = Pnt3.fromSpherical(this.controller.spherical);
    this.isFirstFrame = true;
  }

  async ngAfterViewInit() {
    this.world = new Gg3dWorld({ visualScene: new ThreeSceneComponent() });
    await this.world.init();
    this.viewModeController = new ViewModeController(this.world.visualScene.nativeScene!, this.ambientLight);
    this.viewModeController.onFrameAll = () => this.frameAll();
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
    this.setupCameraController();
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
        for (const f of this._viewFilters) {
          f.meshes = [];
        }
        this.uiGroups = null;
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
        this.meshes = object.children;
        for (const f of this._viewFilters) {
          f.meshes = this.meshes;
        }
        this.applyViewFilters();
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
        this.frameAll();
        this.cdr.markForCheck();
      }
    });
  }

  public frameAll(): void {
    if (this.entity) {
      let bounds = { min: { x: -5, y: -5, z: -5 }, max: { x: 5, y: 5, z: 5 } };
      const box = new Box3();
      let hasVisible = false;
      for (const mesh of this.displayMeshes) {
        if (mesh.visible) {
          box.expandByObject(mesh);
          hasVisible = true;
        }
      }
      if (hasVisible) {
        bounds = {
          min: { x: box.min.x, y: box.min.y, z: box.min.z },
          max: { x: box.max.x, y: box.max.y, z: box.max.z },
        };
      }
      const cameraTarget = Pnt3.scalarMult(Pnt3.add(bounds.min, bounds.max), 0.5);
      const radius = Pnt3.dist(bounds.min, bounds.max);
      let phi = this.controller.spherical.phi;
      let theta = this.controller.spherical.theta;
      if (this.isFirstFrame || (phi === 0 && theta === 0)) {
        phi = 1.22;
        theta = -1.32;
        if (!(this.controller instanceof OrbitCameraController)) {
          phi = Math.PI - phi;
          theta += Math.PI;
        }
        this.isFirstFrame = false;
      }
      if (this.controller instanceof OrbitCameraController) {
        this.controller.target = cameraTarget;
        this.controller.spherical = { phi, theta, radius };
      } else {
        this.renderer.position = Pnt3.sub(cameraTarget, Pnt3.fromSpherical({ phi, theta, radius }));
        this.controller.spherical = { phi, theta, radius };
      }
      this.cdr.markForCheck();
    }
  }

  public setViewMode(mode: ViewMode): void {
    this.viewModeController?.setViewMode(mode);
    this.cdr.detectChanges();
  }

  public toggleMesh(mesh: Object3D): void {
    mesh.visible = !mesh.visible;
  }

  public toggleMeshOnly(mesh: Object3D): void {
    for (const m of this.meshes) {
      m.visible = m === mesh;
    }
  }

  public toggleUiGroup(alias: string): void {
    if (!this.uiGroups) return;
    let visible = !this.uiGroups[alias].visible;
    for (const mesh of this.uiGroups[alias].meshes) {
      mesh.visible = visible;
    }
    this.uiGroups[alias].visible = visible;
  }

  public toggleUiGroupOnly(alias: string): void {
    if (!this.uiGroups) return;
    for (const al in this.uiGroups) {
      this.uiGroups[al].visible = al === alias;
    }
    for (const m of this.displayMeshes) {
      m.visible = false;
    }
    for (const m of this.uiGroups[alias].meshes) {
      m.visible = true;
    }
  }

  public toggleAllVisibility(): void {
    if (this.uiGroups) {
      const allVisible = Object.values(this.uiGroups).every(g => g.visible);
      const newState = !allVisible;
      for (const group of Object.values(this.uiGroups)) {
        group.visible = newState;
        for (const mesh of group.meshes) {
          mesh.visible = newState;
        }
      }
    } else {
      const allVisible = this.displayMeshes.every(m => m.visible);
      const newState = !allVisible;
      for (const mesh of this.displayMeshes) {
        mesh.visible = newState;
      }
    }
    this.cdr.markForCheck();
  }

  // TODO use set.intersection after upgrading typescript
  intersection = function <T>(s1: Set<T>, s2: Set<T>): Set<T> {
    const result = new Set<T>();
    for (const element of s2) {
      if (s1.has(element)) {
        result.add(element);
      }
    }
    return result;
  };

  public applyViewFilters() {
    let displayMeshesSet = new Set<Object3D>(this.meshes);
    for (const f of this._viewFilters) {
      displayMeshesSet = this.intersection(displayMeshesSet, new Set<Object3D>(f.listSelectedGroupMeshes()));
    }
    this.displayMeshes = Array.from(displayMeshesSet);
    for (const m of this.meshes) {
      m.visible = false;
    }
    for (const m of this.displayMeshes) {
      m.visible = true;
    }
    this.rebuildUiGroups();
  }

  private rebuildUiGroups() {
    if (this._visibilityGroupFunction) {
      this.uiGroups = {};
      for (const c of this.displayMeshes) {
        const groupId = this._visibilityGroupFunction(c);
        if (!this.uiGroups[groupId]) {
          this.uiGroups[groupId] = { visible: true, meshes: [c] };
        } else {
          this.uiGroups[groupId].meshes.push(c);
        }
      }
    } else {
      this.uiGroups = null;
    }
    this.cdr.markForCheck();
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
