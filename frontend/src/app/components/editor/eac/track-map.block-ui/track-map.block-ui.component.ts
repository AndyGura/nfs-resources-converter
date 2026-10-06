import {
  AfterViewInit,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  ElementRef,
  inject,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { GuiComponent } from '../../gui.component';
import {
  createInlineTickController,
  Entity3d,
  FreeCameraController,
  Gg3dWorld,
  MapGraph,
  Pnt3,
  Point2,
  Point3,
  Qtrn,
  Renderer3dEntity,
} from '@gg-web-engine/core';
import { BehaviorSubject, debounceTime, filter, Subject, takeUntil } from 'rxjs';
import {
  AmbientLight,
  CubeReflectionMapping,
  DoubleSide,
  Material,
  Mesh,
  MeshBasicMaterial,
  Texture,
  TextureLoader,
} from 'three';
import { ThreeGgWorld, ThreeSceneComponent, ThreeVisualTypeDocRepo } from '@gg-web-engine/three';
import { BlockSchema, Resource } from '../../types';
import { ViewMode, ViewModeController } from '../../common/obj-viewer/view-mode-toolbar/view-mode.controller';
import { joinId } from '../../../../utils/join-id';
import {
  findTrackMapAdapter,
  TrackLayout,
  TrackMapAdapter,
  TrackSplineDetailPanel,
  TrackSplinePoint,
} from './track-map-adapters';
import { TrackEntity, TrackMapWorldEntity } from './track-map-world.entity';

// Game coordinates (Y up) -> viewer coordinates (Z up)
function toViewer(p: Point3): Point3 {
  return { x: p.x, y: p.z, z: p.y };
}

// Chunked track viewer shared by TNFS (TRI), NFS2 (TRK), NFS3 (FRD), NFS4 (FRD), NFS5 (CRP), NFS6 and NFSU tracks;
// per-game differences live in a `TrackMapAdapter`, picked by the block class
@Component({
  selector: 'app-track-map-block-ui',
  templateUrl: './track-map.block-ui.component.html',
  styleUrls: ['./track-map.block-ui.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
  standalone: false,
})
export class TrackMapBlockUiComponent extends GuiComponent implements AfterViewInit, OnChanges, OnDestroy {
  @ViewChild('previewCanvasContainer') previewCanvasContainer!: ElementRef<HTMLDivElement>;
  @ViewChild('previewCanvas') previewCanvas!: ElementRef<HTMLCanvasElement>;

  previewLoading$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(true);
  // Texture archives (QFS/FAM) found next to the track, offered in the picker
  textureArchiveOptions$: BehaviorSubject<string[]> = new BehaviorSubject<string[]>([]);
  textureArchiveLoading$: BehaviorSubject<boolean> = new BehaviorSubject<boolean>(false);
  // The loaded texture archive, null when the terrain uses placeholder textures
  textureArchivePath$: BehaviorSubject<string | null> = new BehaviorSubject<string | null>(null);
  private terrainChunksObjLocation: string | undefined;
  // Files written by the track serializer for the chunked preview
  private serializedFiles: string[] = [];

  pointer$: BehaviorSubject<Point3 | null> = new BehaviorSubject<Point3 | null>(null);

  selectedSplineIndex$: BehaviorSubject<number> = new BehaviorSubject<number>(0);
  selectedSplineDetails$: BehaviorSubject<{ title: string; resource: Resource }[]> = new BehaviorSubject<
    { title: string; resource: Resource }[]
  >([]);
  world!: ThreeGgWorld;
  renderer: Renderer3dEntity<ThreeVisualTypeDocRepo> | null = null;
  map: TrackMapWorldEntity | null = null;
  adapter: TrackMapAdapter | null = null;
  controller!: FreeCameraController;
  chunkPositions: Point3[] | null = null;
  splinePoints: TrackSplinePoint[] = [];
  minimapSpline: Point3[] = [];
  isClosed: boolean = true;
  ambientLight: AmbientLight = new AmbientLight(0xffffff, 2);
  viewModeController?: ViewModeController;
  skySphere!: TrackEntity;
  selectionSphere!: TrackEntity;

  private readonly destroyed$: Subject<void> = new Subject<void>();
  // Resolves once the 3D world is set up; inputs can arrive before that
  private markViewReady!: () => void;
  private readonly viewReady: Promise<void> = new Promise(resolve => (this.markViewReady = resolve));

  get viewMode(): ViewMode {
    return this.viewModeController?.viewMode || 'material';
  }

  readonly cdr = inject(ChangeDetectorRef);

  async ngAfterViewInit() {
    this.world = new Gg3dWorld({ visualScene: new ThreeSceneComponent() });
    await this.world.init();
    this.viewModeController = new ViewModeController(this.world.visualScene.nativeScene!, this.ambientLight);
    this.viewModeController.onFrameAll = () => this.placeRendererAtHome();
    this.world.visualScene.nativeScene!.add(this.ambientLight);
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

    let rendererSize$: BehaviorSubject<Point2> = new BehaviorSubject<Point2>({ x: 1, y: 1 });
    this.renderer = this.world.addRenderer(
      this.world.visualScene.factory.createPerspectiveCamera(),
      this.previewCanvas.nativeElement,
      {
        size: rendererSize$.asObservable(),
        background: 0xaaaaaa,
      },
    );
    this.placeRendererAtHome();
    createInlineTickController(this.world)
      .pipe(takeUntil(this.destroyed$))
      .subscribe(() => {
        if (this.renderer) {
          this.skySphere.position = this.renderer.camera.position;
          this.pointer$.next(this.renderer.camera.position);
          if (this.map) {
            this.map.loaderCursor$.next(this.renderer.position);
          }
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
    this.changes.change$
      .pipe(
        takeUntil(this.destroyed$),
        filter(x => !!(this.resourceId && x.startsWith(this.resourceId))),
        debounceTime(3000),
      )
      .subscribe(async () => {
        this.previewLoading$.next(true);
        await this.loadTerrainChunks(this.resourceId);
        await this.loadPreview();
        this.previewLoading$.next(false);
      });

    this.selectedSplineIndex$.pipe(takeUntil(this.destroyed$), debounceTime(250)).subscribe(i => {
      this.updateSplineDetails();
      const splinePoint = this.splinePoints[i];
      if (!this.resourceId || !splinePoint) {
        return;
      }
      const point = toViewer(splinePoint.position);
      this.selectionSphere.position = point;
      if (this.renderer) {
        this.renderer.position = Pnt3.add(
          point,
          Pnt3.rotAround({ x: 10, y: -12, z: 5 }, { x: 0, y: 0, z: 1 }, -splinePoint.orientation),
        );
        this.renderer.rotation = Qtrn.lookAt(this.renderer.position, point, { x: 0, y: 0, z: 1 });
        this.controller.reset();
      }
    });
    this.markViewReady();
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes.hasOwnProperty('resourceSchema')) {
      this.adapter = findTrackMapAdapter(this.resourceSchema?.block_class_mro);
    }
    if (changes.hasOwnProperty('resourceId') || changes.hasOwnProperty('resourceData')) {
      const data = this.resourceData;
      const adapter = this.adapter;
      if (!adapter?.loadLayout) {
        this.applyLayout(
          data && adapter
            ? {
                chunkPositions: adapter.chunkPositions ? adapter.chunkPositions(data) : null,
                splinePoints: adapter.splinePoints
                  ? adapter.splinePoints(data)
                  : (adapter.chunkPositions ? adapter.chunkPositions(data) : []).map(position => ({
                      position,
                      orientation: 0,
                    })),
                isClosed: !adapter.isClosed || adapter.isClosed(data),
              }
            : null,
        );
      }
      this.updateSplineDetails();
      this.previewLoading$.next(true);
      const resourceIdChanged = changes.hasOwnProperty('resourceId');
      this.loadTerrainChunks(adapter ? this.resourceId : undefined).then(async () => {
        await this.viewReady;
        if (resourceIdChanged && this.resourceId && adapter?.textureArchivePatterns) {
          await this.findTextureArchives(adapter.textureArchivePatterns(this.resourceId));
          await this.onTextureArchiveSelected(this.textureArchiveOptions$.value[0] || null, true);
        } else {
          await this.loadPreview();
        }
        this.previewLoading$.next(false);
      });
    }
  }

  private applyLayout(layout: TrackLayout | null) {
    this.chunkPositions = layout?.chunkPositions ? layout.chunkPositions.map(toViewer) : null;
    this.splinePoints = layout ? layout.splinePoints : [];
    this.minimapSpline = this.splinePoints.map(p => toViewer(p.position));
    this.isClosed = !layout || layout.isClosed;
    this.cdr.markForCheck();
  }

  private async findTextureArchives(patterns: string[]) {
    let found: string[] = [];
    try {
      found = await this.mainService.api.findFiles(patterns);
    } catch (err) {
      console.warn('Could not look up texture archives', err);
    }
    this.textureArchiveOptions$.next(found);
  }

  async browseTextureArchive() {
    const [path] = await this.mainService.api.openFileDialog();
    if (!path) {
      return;
    }
    const normalized = path.replace(/\\/g, '/');
    if (!this.textureArchiveOptions$.value.includes(normalized)) {
      this.textureArchiveOptions$.next([...this.textureArchiveOptions$.value, normalized]);
    }
    await this.onTextureArchiveSelected(normalized);
  }

  // Picker label: the path relative to the folder where the track file lies
  textureArchiveLabel(path: string): string {
    const id = this.resourceId || '';
    const dir = id.substring(0, Math.max(id.lastIndexOf('/'), id.lastIndexOf('\\')) + 1);
    const parentDir = dir.substring(0, Math.max(dir.lastIndexOf('/', dir.length - 2), 0) + 1);
    if (dir && path.startsWith(dir)) {
      return path.substring(dir.length);
    }
    if (parentDir && path.startsWith(parentDir)) {
      return '../' + path.substring(parentDir.length);
    }
    return path;
  }

  private setSkyTexture(texture: Texture | null) {
    const material = (this.skySphere.object3D!.nativeMesh as Mesh).material as MeshBasicMaterial;
    material.map = texture;
    material.needsUpdate = true;
  }

  async onTextureArchiveSelected(path: string | null, force: boolean = false) {
    if (!force && this.textureArchivePath$.value == path) {
      return;
    }
    this.textureArchiveLoading$.next(true);
    try {
      if (!path) {
        this.setSkyTexture(null);
        this.textureArchivePath$.next(null);
        return;
      }
      // Serializes the archive's textures (and, for FAM, props) to disk under `resources/<path>`,
      // where `TrackMapWorldEntity` loads them from
      const files = await this.mainService.api.serializeResource(
        path,
        null,
        this.adapter?.textureArchiveSettings || {},
      );
      if (this.adapter?.hasSkybox) {
        const skyPath = files.find(x => x.endsWith('spherical.png'));
        if (skyPath) {
          const tex = await new TextureLoader().loadAsync(skyPath);
          tex.colorSpace = 'srgb';
          tex.mapping = CubeReflectionMapping;
          this.setSkyTexture(tex);
        } else {
          this.setSkyTexture(null);
        }
      }
      this.textureArchivePath$.next(path);
    } catch (err) {
      if (this.adapter?.hasSkybox) {
        this.setSkyTexture(null);
      }
      this.textureArchivePath$.next(null);
    } finally {
      this.textureArchiveLoading$.next(false);
      await this.loadPreview();
    }
  }

  private async loadTerrainChunks(blockId?: string) {
    if (blockId) {
      const paths = await this.mainService.api.serializeResource(blockId, null, {
        geometry__save_obj: true,
        geometry__save_blend: false,
        geometry__export_to_gg_web_engine: false,
        maps__save_as_chunked: true,
        maps__save_invisible_wall_collisions: false,
        maps__save_terrain_collisions: false,
        maps__save_spherical_skybox_texture: !!this.adapter?.hasSkybox,
        maps__add_props_to_obj: false,
      });
      this.serializedFiles = paths;
      let anyObjPath = paths.find(x => x.endsWith('.obj') && x.includes('terrain_chunk_')) || '';
      this.terrainChunksObjLocation = anyObjPath.substring(0, anyObjPath.indexOf('terrain_chunk_'));
      if (this.adapter?.loadLayout) {
        const hadSpline = this.splinePoints.length > 0;
        this.applyLayout(await this.adapter.loadLayout(paths));
        if (!hadSpline) {
          // the layout wasn't known when the view was set up: fly to the selected spline item now
          this.selectedSplineIndex$.next(this.selectedSplineIndex$.value);
        }
      } else if (this.adapter && !this.adapter.chunkPositions) {
        this.chunkPositions = await this.loadChunkPositionsFile(paths.find(x => x.endsWith('terrain_chunks.json')));
        if (!this.adapter.splinePoints && this.chunkPositions) {
          this.splinePoints = this.chunkPositions.map(position => ({ position: toViewer(position), orientation: 0 }));
          this.minimapSpline = this.chunkPositions;
        }
      }
    } else {
      this.terrainChunksObjLocation = undefined;
      this.serializedFiles = [];
      if (this.adapter?.loadLayout) {
        this.applyLayout(null);
      }
    }
  }

  private async loadChunkPositionsFile(path: string | undefined): Promise<Point3[] | null> {
    if (!path) {
      return null;
    }
    try {
      const positions: Point3[] = await (await fetch(path)).json();
      return positions.map(toViewer);
    } catch (err) {
      console.warn('Could not load terrain chunk positions', err);
      return null;
    }
  }

  // Folder with terrain textures (`<name>.png`), null for placeholder textures
  private get terrainTexturesPath(): string | null {
    if (this.adapter?.bundledTextures) {
      return this.terrainChunksObjLocation ? `${this.terrainChunksObjLocation}textures` : null;
    }
    const textureArchivePath = this.textureArchivePath$.value;
    return (
      textureArchivePath &&
      'resources/' +
        textureArchivePath
          .split('/')
          .filter(x => !!x)
          .join('/')
    );
  }

  onPointerChange(pos: Point3) {
    if (!this.renderer) {
      return;
    }
    this.renderer.position = pos;
  }

  private updateSplineDetails() {
    const panels: TrackSplineDetailPanel[] = this.adapter?.splineDetailPanels || [];
    const data = this.resourceData;
    if (!this.resourceId || !data || !panels.length) {
      this.selectedSplineDetails$.next([]);
      return;
    }
    const i = this.selectedSplineIndex$.value;
    this.selectedSplineDetails$.next(
      panels.map(panel => {
        const entryIndex = Math.floor(i / panel.itemsPerEntry);
        return {
          title: panel.title,
          resource: {
            id: joinId(this.resourceId!, `${panel.field}/${entryIndex}`),
            data: (data[panel.field] || [])[entryIndex],
            schema: (this.resourceSchema?.fields || []).find(
              (x: { name: string; schema: BlockSchema }) => x.name === panel.field,
            )?.schema.child_schema,
            name: '',
          },
        };
      }),
    );
  }

  private async loadPreview() {
    if (!this.resourceData || !this.adapter) return;
    if (!this.terrainChunksObjLocation || !this.chunkPositions) {
      return;
    }
    const chunkNodes = this.chunkPositions.map((position: Point3, i: number) => ({
      path: `${this.terrainChunksObjLocation}terrain_chunk_${i}`,
      position,
      loadOptions: {},
    }));
    const chunksGraph = this.adapter.chunkGraph
      ? this.adapter.chunkGraph(chunkNodes)
      : MapGraph.fromMapArray(chunkNodes, this.isClosed);
    this.unloadPreview();
    this.map = new TrackMapWorldEntity(
      chunksGraph,
      this.terrainTexturesPath,
      this.mainService.hideHiddenFields$,
      this.adapter,
      this.terrainChunksObjLocation,
      this.serializedFiles,
    );
    this.world.addEntity(this.map);
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

  public placeRendererAtHome(): void {
    if (this.renderer) {
      this.renderer.camera.position = { x: 0, y: 0, z: 2.5 };
      this.renderer.camera.rotation = Qtrn.lookAt(
        this.renderer.camera.position,
        Pnt3.add(this.renderer.camera.position, Pnt3.Y),
        Pnt3.Z,
      );
    }
    if (this.controller) {
      this.controller.reset();
    }
  }

  public setViewMode(mode: ViewMode): void {
    this.viewModeController?.setViewMode(mode);
    this.cdr.detectChanges();
  }

  ngOnDestroy(): void {
    this.viewModeController?.dispose();
    this.destroyed$.next();
    this.destroyed$.complete();
  }
}
