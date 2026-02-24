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
  BufferGeometry,
  ClampToEdgeWrapping,
  EdgesGeometry,
  Group,
  LineBasicMaterial,
  LineSegments,
  Material,
  Mesh,
  MeshBasicMaterial,
  MeshLambertMaterial,
  MeshPhongMaterial,
  MeshStandardMaterial,
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

  @Output() onObjectLoaded: EventEmitter<Object3D> = new EventEmitter<Object3D>();

  _paths$: BehaviorSubject<[string, string] | null> = new BehaviorSubject<[string, string] | null>(null);

  @ViewChild('previewCanvasContainer') previewCanvasContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('previewCanvas') previewCanvas!: ElementRef<HTMLCanvasElement>;

  private readonly destroyed$: Subject<void> = new Subject<void>();
  world!: ThreeGgWorld;
  renderer!: Renderer3dEntity<ThreeVisualTypeDocRepo>;
  entity: Entity3d<TypeDocOf<ThreeGgWorld>> | null = null;
  controller!: OrbitCameraController;

  meshes: Object3D[] = [];

  viewMode: 'material' | 'wireframe' | 'unlit' | 'edges' = 'material';
  originalMaterials: Map<Mesh, Material | Material[]> = new Map();
  edgeLines: LineSegments[] = [];
  meshToEdgeLines: Map<Mesh, LineSegments> = new Map();
  ambientLight!: AmbientLight;

  meshesWithViewModeMaterials: Set<Mesh> = new Set();
  controllerManagedMaterials: Map<Mesh, Material | Material[]> = new Map();

  constructor(private readonly cdr: ChangeDetectorRef) {
  }

  async ngAfterViewInit() {
    this.world = new Gg3dWorld({ visualScene: new ThreeSceneComponent() });
    await this.world.init();
    this.ambientLight = new AmbientLight(0xffffff, 2);
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
    this.controller = new OrbitCameraController(this.renderer, {
      mouseOptions: { canvas: this.previewCanvas.nativeElement },
      orbiting: { sensitivityX: 2, sensitivityY: 2 },
      orbitingElasticity: 30,
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
        this.meshes = object.children.filter(child => {
          return !(child instanceof LineSegments) && child.name && child.name.trim() !== '';
        });
        this.meshes.sort((a, b) => (a.name > b.name ? 1 : -1));

        this.originalMaterials.clear();
        this.controllerManagedMaterials.clear();
        this.meshesWithViewModeMaterials.clear();
        this.clearEdgeLines();

        object.traverse(x => {
          if (x instanceof Mesh) {
            this.originalMaterials.set(x, x.material instanceof Array ? [...x.material] : x.material.clone());

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
        this.controller.target = Pnt3.scalarMult(Pnt3.add(bounds.min, bounds.max), 0.5);
        this.controller.spherical = { phi: 1.22, theta: -1.32, radius: Pnt3.dist(bounds.min, bounds.max) };
        this.cdr.markForCheck();
      }
    });
  }

  private clearEdgeLines(): void {
    if (this.entity && this.entity.object3D) {
      for (const edgeLine of this.edgeLines) {
        this.entity.object3D.nativeMesh.remove(edgeLine);
        edgeLine.geometry.dispose();
        (edgeLine.material as LineBasicMaterial).dispose();
      }
    }
    this.edgeLines = [];
    this.meshToEdgeLines.clear();
  }

  private applyViewMode(): void {
    if (!this.entity || !this.entity.object3D) return;

    this.clearEdgeLines();

    this.entity.object3D.nativeMesh.traverse((obj: Object3D) => {
      if (obj instanceof Mesh) {
        const originalMaterial = this.originalMaterials.get(obj);
        if (!originalMaterial) return;

        switch (this.viewMode) {
          case 'material':
            if (this.meshesWithViewModeMaterials.has(obj)) {
              const storedMaterial = this.controllerManagedMaterials.get(obj);
              if (storedMaterial) {
                obj.material = storedMaterial;
                this.controllerManagedMaterials.delete(obj);
              }
              this.meshesWithViewModeMaterials.delete(obj);
            }
            this.ambientLight.intensity = 2;
            break;
          case 'wireframe':
            if (!this.meshesWithViewModeMaterials.has(obj)) {
              this.controllerManagedMaterials.set(obj, obj.material);
            }
            const currentMaterial = this.controllerManagedMaterials.get(obj) || obj.material;
            const wireframeMaterials = currentMaterial instanceof Array ? currentMaterial : [currentMaterial];
            const newWireframeMaterials = wireframeMaterials.map(mat => {
              const wireframeMat = new MeshBasicMaterial({
                color: mat instanceof MeshBasicMaterial ? mat.color : 0xffffff,
                wireframe: true,
                transparent: true,
                opacity: 0.8,
              });
              return wireframeMat;
            });
            obj.material = newWireframeMaterials.length === 1 ? newWireframeMaterials[0] : newWireframeMaterials;
            this.meshesWithViewModeMaterials.add(obj);
            this.ambientLight.intensity = 2;
            break;
          case 'unlit':
            if (!this.meshesWithViewModeMaterials.has(obj)) {
              this.controllerManagedMaterials.set(obj, obj.material);
            }
            const currentUnlitMaterial = this.controllerManagedMaterials.get(obj) || obj.material;
            const unlitMaterials = currentUnlitMaterial instanceof Array ? currentUnlitMaterial : [currentUnlitMaterial];
            const newUnlitMaterials = unlitMaterials.map(mat => {
              let textureMap = null;
              let materialColor = 0xffffff;
              if (mat instanceof MeshBasicMaterial) {
                textureMap = mat.map;
                materialColor = mat.color.getHex();
              } else if (mat instanceof MeshLambertMaterial) {
                textureMap = mat.map;
                materialColor = mat.color.getHex();
              } else if (mat instanceof MeshStandardMaterial) {
                textureMap = mat.map;
                materialColor = mat.color.getHex();
              } else if (mat instanceof MeshPhongMaterial) {
                textureMap = mat.map;
                materialColor = mat.color.getHex();
              }
              const unlitMat = new MeshBasicMaterial({
                color: materialColor,
                map: textureMap,
                transparent: mat.transparent,
                opacity: mat.opacity,
              });
              if (unlitMat.map) {
                unlitMat.map.wrapS = ClampToEdgeWrapping;
                unlitMat.map.wrapT = ClampToEdgeWrapping;
                setupNfs1Texture(unlitMat.map);
              }
              return unlitMat;
            });
            obj.material = newUnlitMaterials.length === 1 ? newUnlitMaterials[0] : newUnlitMaterials;
            this.meshesWithViewModeMaterials.add(obj);
            this.ambientLight.intensity = 0;
            break;
          case 'edges':
            if (this.meshesWithViewModeMaterials.has(obj)) {
              const storedMaterial = this.controllerManagedMaterials.get(obj);
              if (storedMaterial) {
                obj.material = storedMaterial;
                this.controllerManagedMaterials.delete(obj);
              }
              this.meshesWithViewModeMaterials.delete(obj);
            }
            this.ambientLight.intensity = 2;

            const edges = new EdgesGeometry(obj.geometry as BufferGeometry);
            const edgeMaterial = new LineBasicMaterial({ color: 0x000000, linewidth: 2 });
            const edgeLines = new LineSegments(edges, edgeMaterial);
            edgeLines.position.copy(obj.position);
            edgeLines.rotation.copy(obj.rotation);
            edgeLines.scale.copy(obj.scale);

            let effectiveVisibility = obj.visible;
            if (obj.parent && obj.parent instanceof Group && obj.parent !== this.entity!.object3D!.nativeMesh) {
              effectiveVisibility = effectiveVisibility && obj.parent.visible;
            }
            edgeLines.visible = effectiveVisibility;

            this.entity!.object3D!.nativeMesh.add(edgeLines);
            this.edgeLines.push(edgeLines);
            this.meshToEdgeLines.set(obj, edgeLines);
            break;
        }
      }
    });
  }

  public setViewMode(mode: 'material' | 'wireframe' | 'unlit' | 'edges'): void {
    this.viewMode = mode;
    this.applyViewMode();
  }

  public updateEdgeLineVisibility(mesh: Object3D): void {
    if (mesh instanceof Mesh && this.meshToEdgeLines.has(mesh)) {
      const edgeLine = this.meshToEdgeLines.get(mesh)!;
      edgeLine.visible = mesh.visible;
    } else if (mesh instanceof Group) {
      mesh.traverse((child: Object3D) => {
        if (child instanceof Mesh && this.meshToEdgeLines.has(child)) {
          const edgeLine = this.meshToEdgeLines.get(child)!;
          edgeLine.visible = mesh.visible && child.visible;
        }
      });
    }
  }

  public toRGB(color: Color | null): number {
    return ((color?.r || 0) << 16) | ((color?.g || 0) << 8) | (color?.b || 0);
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
