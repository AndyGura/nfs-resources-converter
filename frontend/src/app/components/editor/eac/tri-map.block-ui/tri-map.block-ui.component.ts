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
import { setupNfs1Texture } from '../orip-geometry.block-ui/orip-geometry.block-ui.component';
import { ThreeDisplayObjectComponent, ThreeSceneComponent, ThreeVisualTypeDocRepo } from '@gg-web-engine/three';
import { joinId } from '../../../../utils/join-id';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader';

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
  private readonly objLoader = new OBJLoader();

  public resource: Resource | null = null;
  public isOpenedTrack: boolean = false;

  constructor(public override readonly mapGraph: MapGraph, public readonly famPath: string) {
    super(mapGraph, { loadDepth: 40, inertia: 2 });
  }

  protected override async loadChunk(
    node: MapGraphNodeType,
  ): Promise<[Entity3d<ThreeVisualTypeDocRepo, any>[], LoadResultWithProps<ThreeVisualTypeDocRepo, any>]> {
    const object = await this.objLoader.loadAsync(node.path + '.obj');
    object.position.set(node.position.x, node.position.y, node.position.z);
    object.traverse(node => {
      if (node instanceof Mesh) {
        node.material = this.getTerrainMaterial(
          (node.userData['name'] || node.name)
            .substr((node.userData['name'] || node.name).lastIndexOf('_') + 1)
            .split('.')[0],
        );
      }
    });
    let chunkIndex = +node.path.split('_')[node.path.split('_').length - 1];
    let proxyInstances = (this.resource!.data.proxy_object_instances || [])
      .filter(
        (x: any) =>
          x.reference_road_spline_vertex >= chunkIndex * 4 && x.reference_road_spline_vertex < (chunkIndex + 1) * 4,
      )
      .map((x: any) => ({
        ...x,
        ...this.resource!.data.proxy_objects[x.proxy_object_index],
        position: Pnt3.add(
          { x: x.position.x, y: x.position.z, z: x.position.y },
          {
            x: this.resource!.data.road_spline[x.reference_road_spline_vertex].position.x,
            y: this.resource!.data.road_spline[x.reference_road_spline_vertex].position.z,
            z: this.resource!.data.road_spline[x.reference_road_spline_vertex].position.y,
          },
        ),
        rotation: Qtrn.fromAngle(
          Pnt3.nZ,
          x.rotation + this.resource!.data.road_spline[x.reference_road_spline_vertex].orientation,
        ),
      }));
    const props = (await Promise.all(proxyInstances.map((x: any) => this.loadPropInternal(x)))).filter(
      p => !!p,
    ) as Entity3d<ThreeVisualTypeDocRepo, any>[];
    const entity: Entity3d<ThreeVisualTypeDocRepo, any> = new Entity3d(new ThreeDisplayObjectComponent(object));
    this.addChildren(entity, ...props);
    this.loaded.set(node, [entity, ...props]);
    return [[entity, ...props], null!];
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
          texture.flipY = true;
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

  protected async loadPropInternal(dummy: any): Promise<Entity3d<ThreeVisualTypeDocRepo, any> | null> {
    if (dummy.type == MapPropType.ThreeModel) {
      // 3D model
      const {
        entities: [proxy],
      } = await this.world!.loader.loadGgGlb(
        `${this.famPath}/props/${dummy.proxy_object_data.data.resource_id}/0/body`,
        {
          loadProps: false,
          cachingStrategy: CachingStrategy.Entities,
        },
      );
      proxy.object3D!.nativeMesh.traverse(obj => {
        if (obj instanceof Mesh) {
          fixGltfMaterialsForNfs1(obj, false);
        }
      });
      proxy.position = dummy.position;
      proxy.rotation = dummy.rotation;
      return proxy;
    } else if (dummy.type == MapPropType.Bitmap || dummy.type == MapPropType.TwoSidedBitmap) {
      const textureIds = (resId: number, framesAmount: number) =>
        new Array(framesAmount)
          .fill(null)
          .map((_, i) =>
            this.isOpenedTrack
              ? `${Math.floor(resId / 4) + i}/0000`
              : `0/${(Math.floor(resId / 4) + i).toString().padStart(2, '0')}00`,
          )
          .join(';');

      const object: Object3D = new Group();
      const plane = await this.loadTexturePlaneProp(
        textureIds(
          dummy.proxy_object_data.data.resource_id,
          dummy.flags.is_animated ? dummy.proxy_object_data.data.frame_count : 1,
        ),
        {
          x: dummy.proxy_object_data.data.width,
          y: dummy.proxy_object_data.data.height,
        },
        dummy.proxy_object_data.data.animation_interval,
      );
      object.add(plane);
      if (dummy.type == MapPropType.TwoSidedBitmap) {
        const plane2 = await this.loadTexturePlaneProp(
          textureIds(dummy.proxy_object_data.data.resource_2_id, 1),
          {
            x: dummy.proxy_object_data.data.width_2,
            y: dummy.proxy_object_data.data.height,
          },
          dummy.proxy_object_data.data.animation_interval,
        );
        plane2.rotateY(Math.PI / 2);
        plane2.position.x = dummy.proxy_object_data.data.width / 2;
        plane2.position.y = dummy.proxy_object_data.data.width_2 / 2;
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

  get resource(): Resource | null {
    return this._resource$.getValue();
  }

  @Input()
  set resource(value: Resource | null) {
    this._resource$.next(value);
  }

  _resource$: BehaviorSubject<Resource | null> = new BehaviorSubject<Resource | null>(null);

  @Output('changed') changed: EventEmitter<void> = new EventEmitter<void>();

  previewLoading$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(true);
  previewFamLocation$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);
  previewFamLoading$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);
  private terrainChunksObjLocation: string | undefined;

  pointer$: BehaviorSubject<Point2 | null> = new BehaviorSubject<Point2 | null>(null);

  selectedSplineIndex$: BehaviorSubject<number> = new BehaviorSubject<number>(0);
  selectedSplineItem$: BehaviorSubject<Resource | null> = new BehaviorSubject<Resource | null>(null);
  selectedAiInfoItem$: BehaviorSubject<Resource | null> = new BehaviorSubject<Resource | null>(null);
  selectedTerrainItem$: BehaviorSubject<Resource | null> = new BehaviorSubject<Resource | null>(null);

  famPath: string = '';
  name: string = '';
  world!: Gg3dWorld<ThreeVisualTypeDocRepo, any, ThreeSceneComponent>;
  renderer: Renderer3dEntity<ThreeVisualTypeDocRepo> | null = null;
  map: Nfs1MapWorldEntity | null = null;
  controller!: FreeCameraController;
  roadPath: Point3[] | null = null;
  skySphere!: Entity3d<ThreeVisualTypeDocRepo>;
  selectionSphere!: Entity3d<ThreeVisualTypeDocRepo>;

  private readonly destroyed$: Subject<void> = new Subject<void>();

  constructor(
    private readonly eelDelegate: EelDelegateService,
    private readonly cdr: ChangeDetectorRef,
    private readonly mainService: MainService,
  ) {}

  get previewFamPossibleLocations(): string[] {
    const blockId = this.resource?.id;
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
      (this.resource?.data.road_spline || [])
        .filter((_: any, i: number) => i < (this.resource?.data.terrain_length * 4 || 0))
        .map((d: any) => d.position) || []
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

    this._resource$.pipe(takeUntil(this.destroyed$)).subscribe(async res => {
      this.roadPath =
        res?.data.road_spline
          .map((p: any) => ({
            x: p.position.x,
            y: p.position.z,
            z: p.position.y,
          }))
          .filter((_: any, i: number) => i % 4 === 0)
          .slice(0, res!.data.terrain_length) || null;
      this.previewLoading$.next(true);
      if (this.previewFamPossibleLocations[0]) {
        this.previewFamLocation$.next(this.previewFamPossibleLocations[0]);
        await this.onFamSelected(this.previewFamPossibleLocations[0]);
      }
      await this.loadPreviewGlbPath(res?.id);
      await this.loadPreview();
      this.previewLoading$.next(false);
    });
    this.mainService.dataBlockChange$
      .pipe(
        takeUntil(this.destroyed$),
        filter(([blockId, _]) => !!this.resource && blockId.startsWith(this.resource!.id)),
        debounceTime(3000),
      )
      .subscribe(async () => {
        this.previewLoading$.next(true);
        await this.postTmpUpdates(this.resource?.id);
        await this.loadPreview();
        this.previewLoading$.next(false);
      });

    this.selectedSplineIndex$.pipe(takeUntil(this.destroyed$), debounceTime(250)).subscribe(i => {
      if (this.roadPath) {
        const point = this.roadPath[i];
        if (!point) {
          return;
        }
        this.selectionSphere.position = point;
        const orientation = this.resource!.data.road_spline[i].orientation;
        if (this.renderer) {
          this.renderer.position = Pnt3.add(
            point,
            Pnt3.rotAround({ x: 10, y: -12, z: 5 }, { x: 0, y: 0, z: 1 }, -orientation),
          );
          this.renderer.rotation = Qtrn.lookAt(this.renderer.position, point, { x: 0, y: 0, z: 1 });
        }
      }
      this.selectedSplineItem$.next({
        id: joinId(this.resource!.id, `road_spline/${i}`),
        data: this.resource!.data.road_spline[i],
        schema: (this.resource!.schema.fields || []).find(
          (x: { name: string; schema: BlockSchema }) => x.name === 'road_spline',
        )?.schema.child_schema,
        name: '',
      });
      this.selectedAiInfoItem$.next({
        id: joinId(this.resource!.id, `ai_info/${Math.floor(i / 4)}`),
        data: this.resource!.data.ai_info[Math.floor(i / 4)],
        schema: (this.resource!.schema.fields || []).find(
          (x: { name: string; schema: BlockSchema }) => x.name === 'ai_info',
        )?.schema.child_schema,
        name: '',
      });
      this.selectedTerrainItem$.next({
        id: joinId(this.resource!.id, `terrain/${Math.floor(i / 4)}`),
        data: this.resource!.data.terrain[Math.floor(i / 4)],
        schema: (this.resource!.schema.fields || []).find(
          (x: { name: string; schema: BlockSchema }) => x.name === 'terrain',
        )?.schema.child_schema,
        name: '',
      });
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
        geometry__save_obj: true,
        geometry__save_blend: false,
        geometry__export_to_gg_web_engine: false,
        maps__save_as_chunked: true,
        maps__save_invisible_wall_collisions: false,
        maps__save_terrain_collisions: false,
        maps__save_spherical_skybox_texture: true,
      });
      this.terrainChunksObjLocation = paths[0].substring(0, paths[0].indexOf('terrain_chunk_'));
    } else {
      this.terrainChunksObjLocation = undefined;
    }
  }

  private async loadPreview() {
    if (!this.terrainChunksObjLocation || !this.roadPath) {
      return;
    }
    const chunksGraph = MapGraph.fromMapArray(
      this.roadPath.map((position: Point3, i: number) => ({
        path: `${this.terrainChunksObjLocation}terrain_chunk_${i}`,
        position,
        loadOptions: {
          cachingStrategy: CachingStrategy.Nothing,
          loadProps: false, // props loader is custom and defined in Nfs1MapWorldEntity
        },
      })) || [],
      Pnt3.dist(this.roadPath[0], this.roadPath[this.roadPath.length - 1]) < 100,
    );
    this.unloadPreview();
    this.map = new Nfs1MapWorldEntity(chunksGraph, 'resources/' + this.famPath);
    this.map.resource = this.resource;
    this.map.isOpenedTrack = Pnt3.dist(this.roadPath[0], this.roadPath[this.roadPath.length - 1]) > 100;
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
      this.terrainChunksObjLocation = paths[0].substring(0, paths[0].indexOf('terrain_chunk_'));
    } else {
      this.terrainChunksObjLocation = undefined;
    }
  }

  ngOnDestroy(): void {
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
