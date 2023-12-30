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
import {
  CachingStrategy,
  createInlineTickController,
  Entity3d,
  FreeCameraController,
  Gg3dWorld,
  GgDummy,
  LoadResultWithProps,
  MapGraph,
  MapGraph3dEntity,
  MapGraphNodeType,
  Pnt3,
  Point2,
  Point3,
  Qtrn,
  Renderer3dEntity,
} from '@gg-web-engine/core';
import { BehaviorSubject, debounceTime, filter, Subject, takeUntil, throttleTime } from 'rxjs';
import { EelDelegateService } from '../../../../services/eel-delegate.service';
import {
  AmbientLight,
  ClampToEdgeWrapping,
  CubeReflectionMapping,
  DoubleSide,
  Group,
  Material,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  Object3D,
  PlaneGeometry,
  RepeatWrapping,
  sRGBEncoding,
  TextureLoader,
} from 'three';
import { MainService } from '../../../../services/main.service';
import { GgCurve } from '@gg-web-engine/core/dist/3d/models/gg-meta';
import { setupNfs1Texture } from '../orip-geometry.block-ui/orip-geometry.block-ui.component';
import { ThreeDisplayObjectComponent, ThreeSceneComponent, ThreeVisualTypeDocRepo } from '@gg-web-engine/three';

export enum MapPropType {
  ThreeModel = 'model',
  Bitmap = 'bitmap',
  TwoSidedBitmap = 'two_sided_bitmap',
}

export const fixGltfMaterialsForNfs1: (obj: Mesh, isCar: boolean) => void = (obj, isCar) => {
  let materials = obj.material instanceof Array ? obj.material : [obj.material];
  materials = materials.map(material => {
    if (!(material instanceof MeshBasicMaterial)) {
      // everything is unlit for NFS1
      // TODO fix exporter so NFS1 models will already be unlit
      material = new MeshBasicMaterial({
        map: material instanceof MeshStandardMaterial ? material.map : null,
        side: material.side,
        transparent: !isCar || ['shad'].includes(obj.name),
        alphaTest: !isCar || ['shad'].includes(obj.name) ? 0.5 : 1,
      });
    }
    if (material instanceof MeshBasicMaterial && material.map) {
      material.map.wrapS = ClampToEdgeWrapping;
      material.map.wrapT = ClampToEdgeWrapping;
      setupNfs1Texture(material.map);
      material.map.needsUpdate = true;
    }
    return material;
  });
  obj.material = materials.length > 1 ? materials : materials[0];
};

export class Nfs1MapWorldEntity extends MapGraph3dEntity<ThreeVisualTypeDocRepo, any> {
  public readonly textureLoader = new TextureLoader();
  private readonly terrainMaterials: { [key: string]: MeshBasicMaterial } = {};

  constructor(public override readonly mapGraph: MapGraph, public readonly famPath: string) {
    super(mapGraph, { loadDepth: 50, inertia: 2 });
  }

  protected override async loadChunk(
    node: MapGraphNodeType,
  ): Promise<[Entity3d<ThreeVisualTypeDocRepo, any>[], LoadResultWithProps<ThreeVisualTypeDocRepo, any>]> {
    const [entities, loadResult] = await super.loadChunk(node);
    for (const entity of entities) {
      if (entity.object3D) {
        entity.object3D.nativeMesh.traverse(node => {
          if (node instanceof Mesh) {
            node.material = this.getTerrainMaterial(
              (node.userData['name'] || node.name)
                .substr((node.userData['name'] || node.name).lastIndexOf('_') + 1)
                .split('.')[0],
            );
          }
        });
      }
    }
    const props = (
      await Promise.all(loadResult.meta.dummies.filter(x => x.is_prop).map(dummy => this.loadPropInternal(dummy)))
    ).filter(p => !!p) as Entity3d<ThreeVisualTypeDocRepo, any>[];
    for (const prop of props) {
      prop.position = Pnt3.add(prop.position, node.position);
    }
    const updatedEntities = [...entities, ...props];
    this.loaded.set(node, updatedEntities);
    this.addChildren(...props);
    return [updatedEntities, loadResult];
  }

  getTerrainMaterial(matId: string): Material {
    if (!this.terrainMaterials[matId]) {
      this.terrainMaterials[matId] = new MeshBasicMaterial({ side: DoubleSide, transparent: true, visible: false });
      this.textureLoader
        .loadAsync(`${this.famPath}/background/${matId}.png`)
        .then(texture => {
          texture.wrapS = RepeatWrapping;
          texture.wrapT = ClampToEdgeWrapping;
          setupNfs1Texture(texture);
          texture.flipY = false;
          this.terrainMaterials[matId].map = texture;
          this.terrainMaterials[matId].needsUpdate = true;
          this.terrainMaterials[matId].visible = true;
        })
        .catch(err => {
          console.warn(`Problem with loading terrain material ${matId}`);
        });
    }
    return this.terrainMaterials[matId];
  }

  protected async loadPropInternal(dummy: GgDummy): Promise<Entity3d<ThreeVisualTypeDocRepo, any> | null> {
    if (dummy.type == MapPropType.ThreeModel) {
      // 3D model
      const {
        entities: [proxy],
      } = await this.world!.loader.loadGgGlb(`${this.famPath}/props/${dummy['model_ref_id']}/0/body`, {
        loadProps: false,
        cachingStrategy: CachingStrategy.Entities,
      });
      proxy.object3D!.nativeMesh.traverse(obj => {
        if (obj instanceof Mesh) {
          fixGltfMaterialsForNfs1(obj, false);
        }
      });
      proxy.position = dummy.position;
      proxy.rotation = dummy.rotation;
      return proxy;
    } else if (dummy.type == MapPropType.Bitmap || dummy.type == MapPropType.TwoSidedBitmap) {
      const object: Object3D = new Group();
      const plane = await this.loadTexturePlaneProp(
        dummy['texture'],
        {
          x: dummy.width,
          y: dummy.height,
        },
        dummy['animation_interval'],
      );
      object.add(plane);
      if (dummy.type == MapPropType.TwoSidedBitmap) {
        const plane2 = await this.loadTexturePlaneProp(
          dummy['back_texture'],
          {
            x: dummy.width,
            y: dummy.height,
          },
          dummy['animation_interval'],
        );
        plane2.rotateY(Math.PI / 2);
        plane2.position.x = plane2.position.y = dummy.width / 2;
        object.add(plane2);
      }
      const entity = new Entity3d<ThreeVisualTypeDocRepo, any>(new ThreeDisplayObjectComponent(object), null);
      entity.position = dummy.position;
      entity.rotation = dummy.rotation;
      return entity;
    }
    return null;
  }

  private async loadTexturePlaneProp(texture: string, size: Point2, animationInterval: number): Promise<Object3D> {
    const textures = texture.split(';');
    const maps = await Promise.all(
      textures.map(t => this.textureLoader.loadAsync(`${this.famPath}/foreground/${t}.png`)),
    );
    const materials = maps.map(map => {
      setupNfs1Texture(map);
      return new MeshBasicMaterial({ map, alphaTest: 0.5, transparent: true, side: DoubleSide });
    });
    const plane = new Mesh(new PlaneGeometry(size.x, size.y), materials[0]);
    plane.rotateX(Math.PI / 2);
    plane.position.set(0, 0, size.y / 2);
    if (materials.length > 1) {
      let i = -1;
      // TODO where to unsubscribe?
      createInlineTickController(this.world!)
        .pipe(throttleTime(animationInterval && !isNaN(+animationInterval) ? +animationInterval : 250))
        .subscribe(() => {
          i = (i + 1) % materials.length;
          plane.material = materials[i];
        });
    }
    return plane;
  }
}

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
  }

  @Input() set resourceData(value: ReadData | null) {
    this._resourceData$.next(value);
  }

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  previewLoading$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(true);
  previewFamLocation$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);
  previewFamLoading$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);
  private previewGlbPath: string | undefined;

  selectedSplineIndex$: BehaviorSubject<number> = new BehaviorSubject<number>(0);
  pointer$: BehaviorSubject<Point2 | null> = new BehaviorSubject<Point2 | null>(null);

  famPath: string = '';
  name: string = '';
  world!: Gg3dWorld<ThreeVisualTypeDocRepo, any, ThreeSceneComponent>;
  renderer: Renderer3dEntity<ThreeVisualTypeDocRepo> | null = null;
  map: Nfs1MapWorldEntity | null = null;
  roadPath: GgCurve | null = null;
  controller!: FreeCameraController;
  skySphere!: Entity3d<ThreeVisualTypeDocRepo>;
  selectionSphere!: Entity3d<ThreeVisualTypeDocRepo>;

  private readonly destroyed$: Subject<void> = new Subject<void>();

  constructor(
    private readonly eelDelegate: EelDelegateService,
    private readonly cdr: ChangeDetectorRef,
    private readonly mainService: MainService,
  ) {}

  get previewFamPossibleLocations(): string[] {
    const blockId = this.resourceData?.block_id;
    if (blockId) {
      return [
        blockId.substring(0, blockId.indexOf('MISC')) +
          'ETRACKFM' +
          blockId.substr(blockId.indexOf('MISC') + 4, 4) +
          '_001.FAM',
        blockId.substring(0, blockId.indexOf('MISC')) +
          'GTRACKFM' +
          blockId.substr(blockId.indexOf('MISC') + 4, 4) +
          '_001.FAM',
        blockId.substring(0, blockId.indexOf('MISC')) +
          'NTRACKFM' +
          blockId.substr(blockId.indexOf('MISC') + 4, 4) +
          '_M01.FAM',
        blockId.substring(0, blockId.indexOf('MISC')) +
          'NTRACKFM' +
          blockId.substr(blockId.indexOf('MISC') + 4, 4) +
          '_R01.FAM',
        blockId.substring(0, blockId.indexOf('MISC')) +
          'NTRACKFM' +
          blockId.substr(blockId.indexOf('MISC') + 4, 4) +
          '_T01.FAM',
      ];
    } else {
      return [];
    }
  }

  get roadSpline(): Point3[] {
    return (
      (this.resourceData?.value.road_spline.value || [])
        .filter((_: any, i: number) => i < (this.resourceData?.value.terrain_length.value * 4 || 0))
        .map((d: any) => ({
          x: d.value.position.value.x.value,
          y: d.value.position.value.y.value,
          z: d.value.position.value.z.value,
        })) || []
    );
  }

  async ngAfterViewInit() {
    this.world = new Gg3dWorld(new ThreeSceneComponent(), {
      init: async () => {},
      simulate: () => {},
      loader: {
        loadFromGgGlb: async (...args: any[]) => [],
      },
    } as any);
    await this.world.init();
    this.skySphere = new Entity3d(
      this.world.visualScene.factory.createPrimitive({ shape: 'SPHERE', radius: 1000 }, { color: 0xffffff }),
    );
    ((this.skySphere.object3D!.nativeMesh as Mesh).material as Material).side = DoubleSide;
    this.skySphere.rotation = Qtrn.fromEuler({ x: Math.PI / 2, y: 0, z: 0 }); // make it face towards Z
    this.world.addEntity(this.skySphere);
    this.selectionSphere = new Entity3d(
      this.world.visualScene.factory.createPrimitive(
        { shape: 'SPHERE', radius: 0.5 },
        {
          color: 0xff0000,
          shading: 'unlit',
        },
      ),
    );
    ((this.selectionSphere.object3D!.nativeMesh as Mesh).material as Material).opacity = 0.4;
    ((this.selectionSphere.object3D!.nativeMesh as Mesh).material as Material).transparent = true;
    this.world.addEntity(this.selectionSphere);

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
    this.renderer.camera.position = { x: 0, y: 0, z: 2.5 };
    this.renderer.camera.rotation = Qtrn.lookAt(
      this.renderer.camera.position,
      Pnt3.add(this.renderer.camera.position, Pnt3.Y),
      Pnt3.Z,
    );
    createInlineTickController(this.world)
      .pipe(takeUntil(this.destroyed$))
      .subscribe(() => {
        if (this.renderer) {
          this.skySphere.position = this.renderer.camera.position;
          this.pointer$.next(this.renderer.camera.position);
        }
      });

    this.controller = new FreeCameraController(this.world.keyboardInput, this.renderer, {
      mouseOptions: {
        canvas: this.previewCanvas.nativeElement,
        pointerLock: true,
      },
      keymap: 'wasd+arrows',
      movementOptions: { speed: 1 },
      ignoreMouseUnlessPointerLocked: true,
      ignoreKeyboardUnlessPointerLocked: true,
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

    this._resourceData$.pipe(takeUntil(this.destroyed$)).subscribe(async data => {
      this.previewLoading$.next(true);
      if (this.previewFamPossibleLocations[0]) {
        this.previewFamLocation$.next(this.previewFamPossibleLocations[0]);
        await this.onFamSelected(this.previewFamPossibleLocations[0]);
      }
      await this.loadPreviewGlbPath(data?.block_id);
      await this.loadPreview();
      this.previewLoading$.next(false);
    });
    this.mainService.dataBlockChange$
      .pipe(
        takeUntil(this.destroyed$),
        filter(([blockId, _]) => !!this.resourceData && blockId.startsWith(this.resourceData!.block_id)),
        debounceTime(3000),
      )
      .subscribe(async () => {
        this.previewLoading$.next(true);
        await this.postTmpUpdates(this.resourceData?.block_id);
        await this.loadPreview();
        this.previewLoading$.next(false);
      });

    this.selectedSplineIndex$.pipe(takeUntil(this.destroyed$), debounceTime(250)).subscribe(i => {
      if (this.roadPath) {
        const point = this.roadPath.points[i];
        if (!point) {
          return;
        }
        this.selectionSphere.position = point;
        const orientation = this.resourceData!.value.road_spline.value[i].value.orientation.value;
        if (this.renderer) {
          this.renderer.position = Pnt3.add(
            point,
            Pnt3.rotAround({ x: 10, y: -12, z: 5 }, { x: 0, y: 0, z: 1 }, -orientation),
          );
          this.renderer.rotation = Qtrn.lookAt(this.renderer.position, point, { x: 0, y: 0, z: 1 });
        }
      }
    });
  }

  async onFamSelected(path: string) {
    if (path == 'custom' || this.famPath == path) {
      return;
    }
    this.famPath = path;
    this.previewFamLoading$.next(true);
    try {
      const files = await this.eelDelegate.serializeResource(path, {
        geometry__save_obj: false,
        geometry__save_blend: false,
        geometry__export_to_gg_web_engine: true,
      });
      const loader = new TextureLoader();
      const skyPath = files.find(x => x.endsWith('spherical.png'));
      if (skyPath) {
        const tex = await loader.loadAsync(skyPath);
        tex.encoding = sRGBEncoding;
        tex.mapping = CubeReflectionMapping;
        ((this.skySphere.object3D!.nativeMesh as Mesh).material as MeshBasicMaterial).map = tex;
      } else {
        ((this.skySphere.object3D!.nativeMesh as Mesh).material as MeshBasicMaterial).map = null;
      }
      ((this.skySphere.object3D!.nativeMesh as Mesh).material as MeshBasicMaterial).needsUpdate = true;
    } finally {
      this.previewFamLoading$.next(false);
    }
    await this.loadPreview();
  }

  private async loadPreviewGlbPath(blockId: string | undefined) {
    if (blockId) {
      const paths = await this.eelDelegate.serializeResource(blockId, {
        geometry__save_obj: false,
        geometry__save_blend: false,
        geometry__export_to_gg_web_engine: true,
        maps__save_as_chunked: true,
        maps__save_invisible_wall_collisions: false,
        maps__save_terrain_collisions: false,
        maps__save_spherical_skybox_texture: true,
      });
      this.previewGlbPath = paths.find(x => x.endsWith('map.glb'))!;
    } else {
      this.previewGlbPath = undefined;
    }
  }

  private async loadPreview() {
    if (!this.previewGlbPath) {
      return;
    }
    const { meta } = await this.world!.loader.loadGgGlb(
      this.previewGlbPath.substring(0, this.previewGlbPath.length - 4),
      {
        loadProps: false,
      },
    );
    this.roadPath = meta.curves.find(curve => curve.name === 'road_path')!;
    const chunksGraph = MapGraph.fromMapArray(
      this.roadPath.points
        .filter((_: any, i: number) => i % 4 === 0)
        .map((position: Point3, i: number) => ({
          path: `${this.previewGlbPath!.substring(0, this.previewGlbPath!.lastIndexOf('/'))}/terrain_chunk_${i}`,
          position,
          loadOptions: {
            cachingStrategy: CachingStrategy.Nothing,
            loadProps: false, // props loader is custom and defined in Nfs1MapWorldEntity
          },
        })) || [],
      this.roadPath.cyclic,
    );
    this.unloadPreview();
    this.map = new Nfs1MapWorldEntity(chunksGraph, 'resources/' + this.famPath);
    this.map.loaderCursorEntity$.next(this.renderer);
    this.world.addEntity(this.map!);
    this.cdr.markForCheck();
  }

  private unloadPreview() {
    if (this.map) {
      this.world.removeEntity(this.map);
      this.map.dispose();
      this.map = null;
      this.cdr.markForCheck();
    }
  }

  private async postTmpUpdates(blockId: string | undefined) {
    if (blockId) {
      const paths = await this.eelDelegate.serializeResourceTmp(
        blockId,
        Object.entries(this.mainService.changedDataBlocks)
          .filter(([id, _]) => id != '__has_external_changes__' && id.startsWith(blockId))
          .map(([id, value]) => {
            return { id, value };
          }),
        {
          geometry__save_obj: false,
          geometry__save_blend: false,
          geometry__export_to_gg_web_engine: true,
          maps__save_as_chunked: true,
          maps__save_invisible_wall_collisions: false,
          maps__save_terrain_collisions: false,
          maps__save_spherical_skybox_texture: true,
        },
      );
      this.previewGlbPath = paths.find(x => x.endsWith('map.glb'))!;
    } else {
      this.previewGlbPath = undefined;
    }
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }

  protected readonly Math = Math;
  protected readonly Object = Object;
}
