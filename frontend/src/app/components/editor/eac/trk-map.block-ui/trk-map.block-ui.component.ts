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
import { BehaviorSubject, debounceTime, distinctUntilChanged, filter, Subject, takeUntil, throttleTime } from 'rxjs';
import { EelDelegateService } from '../../../../services/eel-delegate.service';
import {
  AmbientLight,
  CubeReflectionMapping,
  DoubleSide,
  Group,
  Material,
  Mesh,
  MeshBasicMaterial,
  Object3D,
  PlaneGeometry,
  RepeatWrapping,
  Texture,
  TextureLoader,
} from 'three';
import { MainService } from '../../../../services/main.service';
import { ThreeDisplayObjectComponent, ThreeSceneComponent, ThreeVisualTypeDocRepo } from '@gg-web-engine/three';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader';
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader';
import { setupNfs1Texture } from '../../common/obj-viewer/obj-viewer.component';

export enum MapPropType {
  ThreeModel = 'model',
  Bitmap = 'bitmap',
  TwoSidedBitmap = 'two_sided_bitmap',
}

export class Nfs2MapWorldEntity extends MapGraph3dEntity<ThreeVisualTypeDocRepo, any> {
  public readonly textureLoader = new TextureLoader();
  private readonly terrainMaterials: { [key: string]: MeshBasicMaterial } = {};
  private readonly objLoader = new OBJLoader();

  public resource: Resource | null = null;
  public isOpenedTrack: boolean = false;

  constructor(
    public override readonly mapGraph: MapGraph,
    public readonly qfsPath: string | null,
    private readonly hideUnknownEntities$: BehaviorSubject<boolean>,
  ) {
    super(mapGraph, { loadDepth: 40, inertia: 2 });
  }

  private _placeholder: Texture | null = null;
  private _placeholderPromise: Promise<Texture> | null = null;

  unknownEntities: Set<Entity3d> = new Set<Entity3d>();

  override onSpawned(world: Gg3dWorld<ThreeVisualTypeDocRepo, any>) {
    super.onSpawned(world);
    this.hideUnknownEntities$.pipe(distinctUntilChanged(), takeUntil(this._onRemoved$)).subscribe(hide => {
      for (const e of this.unknownEntities) {
        e.visible = !hide;
      }
    });
  }

  async getPlaceholderTexture(): Promise<Texture> {
    if (this._placeholder) return this._placeholder;
    if (!this._placeholderPromise) {
      this._placeholderPromise = this.textureLoader.loadAsync('assets/placeholder_texture.png');
    }
    return this._placeholderPromise;
  }

  private _placeholderTerrain: Texture | null = null;
  private _placeholderTerrainPromise: Promise<Texture> | null = null;

  async getPlaceholderTerrainTexture(): Promise<Texture> {
    if (this._placeholderTerrain) return this._placeholderTerrain;
    if (!this._placeholderTerrainPromise) {
      this._placeholderTerrainPromise = this.textureLoader.loadAsync('assets/placeholder_texture.png').then(texture => {
        texture.wrapS = RepeatWrapping;
        texture.wrapT = RepeatWrapping;
        setupNfs1Texture(texture);
        return texture;
      });
    }
    return this._placeholderTerrainPromise;
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
    let propInstances = (this.resource!.data.props || [])
      .filter((x: any) => x.road_point_idx >= chunkIndex * 4 && x.road_point_idx < (chunkIndex + 1) * 4)
      .map((x: any) => ({
        ...x,
        ...this.resource!.data.prop_descr[x.prop_descr_idx],
        position: Pnt3.add(
          { x: x.position.x, y: x.position.z, z: x.position.y },
          {
            x: this.resource!.data.road_spline[x.road_point_idx].position.x,
            y: this.resource!.data.road_spline[x.road_point_idx].position.z,
            z: this.resource!.data.road_spline[x.road_point_idx].position.y,
          },
        ),
        rotation: Qtrn.fromAngle(Pnt3.nZ, x.rotation),
      }));
    const props = (await Promise.all(propInstances.map((x: any) => this.loadPropInternal(x)))).filter(
      p => !!p,
    ) as Entity3d<ThreeVisualTypeDocRepo, any>[];
    const entity: Entity3d<ThreeVisualTypeDocRepo, any> = new Entity3d({
      object3D: new ThreeDisplayObjectComponent(object),
    });
    this.addChildren(entity, ...props);
    this.loaded.set(node, [entity, ...props]);
    return [[entity, ...props], null!];
  }

  protected override disposeChunk(node: MapGraphNodeType) {
    for (const c of this.loaded.get(node) || []) {
      this.unknownEntities.delete(c as Entity3d);
    }
    super.disposeChunk(node);
  }

  getTerrainMaterial(matId: string): Material {
    if (!this.terrainMaterials[matId]) {
      this.terrainMaterials[matId] = new MeshBasicMaterial({ side: DoubleSide, transparent: true, visible: false });
      if (this.qfsPath) {
        this.textureLoader
          .loadAsync(`${this.qfsPath}/${matId}.png`)
          .then(texture => {
            texture.wrapS = RepeatWrapping;
            texture.wrapT = RepeatWrapping;
            setupNfs1Texture(texture);
            this.terrainMaterials[matId].map = texture;
            this.terrainMaterials[matId].needsUpdate = true;
            this.terrainMaterials[matId].visible = true;
          })
          .catch(err => {
            console.warn(`Problem with loading terrain material ${matId}`);
            this.getPlaceholderTerrainTexture().then(texture => {
              this.terrainMaterials[matId].map = texture;
              this.terrainMaterials[matId].needsUpdate = true;
              this.terrainMaterials[matId].visible = true;
            });
          });
      } else {
        this.getPlaceholderTerrainTexture().then(texture => {
          this.terrainMaterials[matId].map = texture;
          this.terrainMaterials[matId].needsUpdate = true;
          this.terrainMaterials[matId].visible = true;
        });
      }
    }
    return this.terrainMaterials[matId];
  }

  protected async loadPropInternal(dummy: any): Promise<Entity3d<ThreeVisualTypeDocRepo, any> | null> {
    let isUnknown = false;
    if (dummy.type == MapPropType.ThreeModel) {
      // 3D model
      let object: ThreeDisplayObjectComponent;
      try {
        if (!this.qfsPath) throw new Error();
        const mtlLoader = new MTLLoader();
        const objLoader = new OBJLoader();
        const mtl = await mtlLoader.loadAsync(`${this.qfsPath}/props/${dummy.data.data.resource_id}/0/material.mtl`);
        mtl.preload();
        objLoader.setMaterials(mtl);
        object = new ThreeDisplayObjectComponent(
          await objLoader.loadAsync(`${this.qfsPath}/props/${dummy.data.data.resource_id}/0/geometry.obj`),
        );
      } catch (err) {
        isUnknown = true;
        object = this.world!.visualScene.factory.createPrimitive(
          { shape: 'SPHERE', radius: 5 },
          { diffuse: await this.getPlaceholderTexture() },
        );
      }
      object.nativeMesh.traverse(x => {
        if (x instanceof Mesh) {
          const materials: Material[] = x.material instanceof Array ? x.material : [x.material];
          for (const m of materials) {
            m.transparent = true;
            m.alphaTest = 0.5;
            if (m instanceof MeshBasicMaterial && m.map) {
              m.map.wrapS = RepeatWrapping;
              m.map.wrapT = RepeatWrapping;
              setupNfs1Texture(m.map);
              m.map.needsUpdate = true;
            }
          }
        }
      });
      const prop = new Entity3d<ThreeVisualTypeDocRepo>({ object3D: object });
      prop.position = dummy.position;
      prop.rotation = dummy.rotation;
      if (isUnknown) {
        this.unknownEntities.add(prop);
        prop.visible = !this.hideUnknownEntities$.getValue();
      }
      this.world!.addEntity(prop);
      return prop;
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
      const [plane, isUnknown] = await this.loadTexturePlaneProp(
        textureIds(dummy.data.data.resource_id, dummy.flags.is_animated ? dummy.data.data.frame_count : 1),
        {
          x: dummy.data.data.width,
          y: dummy.data.data.height,
        },
        dummy.data.data.animation_interval,
      );
      object.add(plane);
      if (dummy.type == MapPropType.TwoSidedBitmap) {
        const [plane2, isUnknown] = await this.loadTexturePlaneProp(
          textureIds(dummy.data.data.resource_id_2, 1),
          {
            x: dummy.data.data.width_2,
            y: dummy.data.data.height,
          },
          dummy.data.data.animation_interval,
        );
        plane2.rotateY(Math.PI / 2);
        plane2.position.x = dummy.data.data.width / 2;
        plane2.position.y = dummy.data.data.width_2 / 2;
        object.add(plane2);
      }
      const entity = new Entity3d<ThreeVisualTypeDocRepo, any>({ object3D: new ThreeDisplayObjectComponent(object) });
      entity.position = dummy.position;
      entity.rotation = dummy.rotation;
      if (isUnknown) {
        this.unknownEntities.add(entity);
        entity.visible = !this.hideUnknownEntities$.getValue();
      }
      return entity;
    }
    return null;
  }

  private async loadTexturePlaneProp(
    texture: string,
    size: Point2,
    animationInterval: number,
  ): Promise<[Object3D, boolean]> {
    const textures = texture.split(';');
    const placeholder = await this.getPlaceholderTexture();
    let isUnknown = false;
    let maps = [];
    if (!this.qfsPath) {
      isUnknown = true;
      maps = textures.map(() => placeholder);
    } else {
      maps = await Promise.all(
        textures.map(t =>
          this.textureLoader.loadAsync(`${this.qfsPath}/foreground/${t}.png`).catch(() => {
            isUnknown = true;
            return placeholder;
          }),
        ),
      );
    }
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
        .pipe(throttleTime(animationInterval && !isNaN(+animationInterval) ? +animationInterval * 1000 : 250))
        .subscribe(() => {
          i = (i + 1) % materials.length;
          plane.material = materials[i];
        });
    }
    return [plane, isUnknown];
  }
}

@Component({
  selector: 'app-trk-map-block-ui',
  templateUrl: './trk-map.block-ui.component.html',
  styleUrls: ['./trk-map.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class TrkMapBlockUiComponent implements GuiComponentInterface, AfterViewInit, OnDestroy {
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
  previewQfsLocation$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);
  previewQfsLoading$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);
  private terrainChunksObjLocation: string | undefined;

  pointer$: BehaviorSubject<Point3 | null> = new BehaviorSubject<Point3 | null>(null);

  selectedSplineIndex$: BehaviorSubject<number> = new BehaviorSubject<number>(0);
  qfsPath: string | null = null;
  name: string = '';
  world!: Gg3dWorld<ThreeVisualTypeDocRepo, any, ThreeSceneComponent>;
  renderer: Renderer3dEntity<ThreeVisualTypeDocRepo> | null = null;
  map: Nfs2MapWorldEntity | null = null;
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

  async ngAfterViewInit() {
    this.world = new Gg3dWorld(new ThreeSceneComponent(), {
      init: async () => {},
      simulate: () => {},
      loader: {
        loadFromGgGlb: async (...args: any[]) => [],
      },
    } as any);
    await this.world.init();
    this.skySphere = new Entity3d({
      object3D: this.world.visualScene.factory.createPrimitive(
        {
          shape: 'SPHERE',
          radius: 1000,
        },
        { color: 0xffffff },
      ),
    });
    ((this.skySphere.object3D!.nativeMesh as Mesh).material as Material).side = DoubleSide;
    this.world.addEntity(this.skySphere);
    this.selectionSphere = new Entity3d({
      object3D: this.world.visualScene.factory.createPrimitive(
        { shape: 'SPHERE', radius: 0.5 },
        {
          color: 0xff0000,
          shading: 'unlit',
        },
      ),
    });
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
      cameraLinearSpeed: 40,
      cameraBoostMultiplier: 4,
      cameraMovementElasticity: 100,
      cameraRotationElasticity: 30,
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
      this.roadPath = this.resource?.data.block_positions.map((p: Point3) => ({
        x: p.x,
        y: p.z,
        z: p.y,
      }));
      this.previewLoading$.next(true);
      if (res) {
        this.previewQfsLocation$.next(res.id.substring(0, res.id.indexOf('.TRK')) + '0.QFS');
        await this.loadTerrainChunks(res.id);
        await this.onQfsSelected(this.previewQfsLocation$.value!);
      } else {
        await this.loadTerrainChunks();
        await this.loadPreview();
      }
      this.previewLoading$.next(false);
    });
    this.mainService.dataBlockChange$
      .pipe(
        takeUntil(this.destroyed$),
        filter(([blockId, _]) => !!this.resource && blockId.startsWith(this.resource!.id)),
        debounceTime(3000),
      )
      .subscribe(async () => {
        this.roadPath = this.resource?.data.block_positions.map((p: Point3) => ({
          x: p.x,
          y: p.z,
          z: p.y,
        }));
        this.previewLoading$.next(true);
        await this.postTmpUpdates(this.resource?.id);
        await this.loadPreview();
        this.previewLoading$.next(false);
      });

    this.selectedSplineIndex$.pipe(takeUntil(this.destroyed$), debounceTime(250)).subscribe(i => {
      if (this.resource) {
        let point = this.resource.data.block_positions[i];
        if (!point) {
          return;
        }
        point = { x: point.x, y: point.z, z: point.y };
        this.selectionSphere.position = point;
        const orientation = 0;
        if (this.renderer) {
          this.renderer.position = Pnt3.add(
            point,
            Pnt3.rotAround({ x: 10, y: -12, z: 5 }, { x: 0, y: 0, z: 1 }, -orientation),
          );
          this.renderer.rotation = Qtrn.lookAt(this.renderer.position, point, { x: 0, y: 0, z: 1 });
          this.controller.reset();
        }
      }
    });
  }

  async onQfsSelected(path: string) {
    if (this.qfsPath == path) {
      return;
    }
    this.previewQfsLoading$.next(true);
    try {
      const files = await this.eelDelegate.serializeResource(path);
      const loader = new TextureLoader();
      const skyPath = files.find(x => x.endsWith('spherical.png'));
      if (skyPath) {
        const tex = await loader.loadAsync(skyPath);
        tex.colorSpace = 'srgb';
        tex.mapping = CubeReflectionMapping;
        ((this.skySphere.object3D!.nativeMesh as Mesh).material as MeshBasicMaterial).map = tex;
      } else {
        ((this.skySphere.object3D!.nativeMesh as Mesh).material as MeshBasicMaterial).map = null;
      }
      ((this.skySphere.object3D!.nativeMesh as Mesh).material as MeshBasicMaterial).needsUpdate = true;
      this.qfsPath = path;
    } catch (err) {
      ((this.skySphere.object3D!.nativeMesh as Mesh).material as MeshBasicMaterial).map = null;
      ((this.skySphere.object3D!.nativeMesh as Mesh).material as MeshBasicMaterial).needsUpdate = true;
      this.qfsPath = null;
    } finally {
      this.previewQfsLoading$.next(false);
    }
    await this.loadPreview();
  }

  private async loadTerrainChunks(blockId?: string) {
    if (blockId) {
      const paths = await this.eelDelegate.serializeResource(blockId, {
        geometry__save_obj: true,
        geometry__save_blend: false,
        geometry__export_to_gg_web_engine: false,
        maps__save_as_chunked: true,
        maps__save_invisible_wall_collisions: false,
        maps__save_terrain_collisions: false,
        maps__save_spherical_skybox_texture: true,
        maps__add_props_to_obj: false,
      });
      let anyObjPath = paths.find(x => x.endsWith('.obj')) || '';
      this.terrainChunksObjLocation = anyObjPath.substring(0, anyObjPath.indexOf('terrain_chunk_'));
    } else {
      this.terrainChunksObjLocation = undefined;
    }
  }

  onPointerChange(pos: Point3) {
    if (!this.renderer) {
      return;
    }
    this.renderer.position = pos;
  }

  private async loadPreview() {
    if (!this.terrainChunksObjLocation || !this.roadPath) {
      return;
    }
    const chunksGraph = MapGraph.fromMapArray(
      this.roadPath.map((position: Point3, i: number) => ({
        path: `${this.terrainChunksObjLocation}terrain_chunk_${i}`,
        position,
        loadOptions: {},
      })) || [],
      true,
    );
    this.unloadPreview();
    this.map = new Nfs2MapWorldEntity(
      chunksGraph,
      this.qfsPath && 'resources/' + this.qfsPath,
      this.mainService.hideHiddenFields$,
    );
    this.map.resource = this.resource;
    this.map.isOpenedTrack = false;

    createInlineTickController(this.world)
      .pipe(takeUntil(this.destroyed$))
      .subscribe(() => {
        if (this.map && this.renderer) {
          this.map.loaderCursor$.next(this.renderer.position);
        }
      });
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
          geometry__save_obj: true,
          geometry__save_blend: false,
          geometry__export_to_gg_web_engine: false,
          maps__save_as_chunked: true,
          maps__save_invisible_wall_collisions: false,
          maps__save_terrain_collisions: false,
          maps__save_spherical_skybox_texture: true,
          maps__add_props_to_obj: false,
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
