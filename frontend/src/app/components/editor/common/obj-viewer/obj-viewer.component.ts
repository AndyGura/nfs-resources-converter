import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  Input,
  OnDestroy,
  ViewChild,
} from '@angular/core';
import { BehaviorSubject, Subject, takeUntil } from 'rxjs';
import { Entity3d, Gg3dWorld, OrbitCameraController, Pnt3, Point2, Renderer3dEntity } from '@gg-web-engine/core';
import { ThreeDisplayObjectComponent, ThreeSceneComponent, ThreeVisualTypeDocRepo } from '@gg-web-engine/three';
import { AmbientLight, ClampToEdgeWrapping, Material, Mesh, MeshBasicMaterial, NearestFilter, Texture } from 'three';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader';
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader';

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
  get paths(): [string, string] | null {
    return this._paths$.getValue();
  }

  @Input()
  set paths(value: [string, string] | null) {
    this._paths$.next(value);
  }

  _paths$: BehaviorSubject<[string, string] | null> = new BehaviorSubject<[string, string] | null>(null);

  @ViewChild('previewCanvasContainer') previewCanvasContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('previewCanvas') previewCanvas!: ElementRef<HTMLCanvasElement>;

  private readonly destroyed$: Subject<void> = new Subject<void>();
  world!: Gg3dWorld<ThreeVisualTypeDocRepo, any, ThreeSceneComponent>;
  renderer!: Renderer3dEntity<ThreeVisualTypeDocRepo>;
  entity: Entity3d<ThreeVisualTypeDocRepo> | null = null;
  controller!: OrbitCameraController;

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

    this._paths$.pipe(takeUntil(this.destroyed$)).subscribe(async paths => {
      if (this.entity) {
        this.world.removeEntity(this.entity);
        this.entity.dispose();
        this.entity = null;
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

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
