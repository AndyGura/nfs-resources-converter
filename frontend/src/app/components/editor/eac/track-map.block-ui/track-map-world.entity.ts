import {
  Entity3d,
  GgDummy,
  GgWorld,
  LoadResultWithProps,
  MapGraph,
  MapGraph3dEntity,
  MapGraphNodeType,
  Qtrn,
} from '@gg-web-engine/core';
import { BehaviorSubject, distinctUntilChanged, takeUntil } from 'rxjs';
import {
  DoubleSide,
  Euler,
  Material,
  Mesh,
  MeshBasicMaterial,
  Object3D,
  Quaternion,
  RepeatWrapping,
  SphereGeometry,
  Texture,
  TextureLoader,
} from 'three';
import { ThreeDisplayObjectComponent, ThreeGgWorld } from '@gg-web-engine/three';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js';
import { setupNfs1Texture } from '../../common/obj-viewer/obj-viewer.component';
import { TrackMapAdapter } from './track-map-adapters';
import { meshTextureName, TrackPropsAssets, TrackPropsController } from './track-props-controller';

// TODO use this from gg-web-engine after next release
export type TypeDocOf<W extends GgWorld<any, any>> =
  W extends GgWorld<infer D, infer R, infer TypeDoc> ? TypeDoc : never;

export type TrackEntity = Entity3d<TypeDocOf<ThreeGgWorld>>;

// A dummy of "<scene>_extra.json" written by the converter next to an OBJ, in the format of gg-web-engine meta
// dummies (what the game gets from the ".meta" of the same scene exported to gg-web-engine)
function extraJsonDummyToGgDummy(dummy: any): GgDummy {
  const [x, y, z] = dummy.position || [0, 0, 0];
  let rotation;
  if (dummy.quaternion) {
    const [qw, qx, qy, qz] = dummy.quaternion;
    rotation = { x: qx, y: qy, z: qz, w: qw };
  } else if (dummy.rotation) {
    // Blender "XYZ" Euler angles, which is three.js "ZYX" order
    const q = new Quaternion().setFromEuler(new Euler(dummy.rotation[0], dummy.rotation[1], dummy.rotation[2], 'ZYX'));
    rotation = { x: q.x, y: q.y, z: q.z, w: q.w };
  } else {
    rotation = Qtrn.O;
  }
  return { ...(dummy.properties || {}), name: dummy.name, position: { x, y, z }, rotation };
}

function setupTerrainTextureDefault(texture: Texture) {
  texture.wrapS = RepeatWrapping;
  texture.wrapT = RepeatWrapping;
  setupNfs1Texture(texture);
}

// Track terrain streamed as OBJ chunks along a MapGraph, textured from `<textureArchivePath>/<name>.png`: a texture
// archive (QFS/FAM) serialized there, or textures the track serializer wrote next to the chunks. Props of a chunk are
// the dummies of its "_extra.json", spawned by the adapter's props controller (the same controllers render tracks in
// nfs-web, see `track-props-controller.ts`), with this entity as their `TrackPropsAssets`.
export class TrackMapWorldEntity extends MapGraph3dEntity<TypeDocOf<ThreeGgWorld>> implements TrackPropsAssets {
  public readonly textureLoader = new TextureLoader();
  private readonly terrainMaterials: { [key: string]: MeshBasicMaterial } = {};
  private readonly objLoader = new OBJLoader();
  private readonly models = new Map<string, Promise<Object3D | null>>();
  private readonly propsController: TrackPropsController | null;

  constructor(
    public override readonly mapGraph: MapGraph,
    public readonly textureArchivePath: string | null,
    private readonly hideUnknownEntities$: BehaviorSubject<boolean>,
    public readonly adapter: TrackMapAdapter,
    // Folder of the serialized chunks: "<chunksLocation>terrain_chunk_<i>.obj"
    public readonly chunksLocation: string,
    // Files written by the track serializer (chunks and what comes with them)
    public readonly serializedFiles: string[] = [],
  ) {
    super(mapGraph, { loadDepth: adapter.loadDepth ?? 40, inertia: 2 });
    this.propsController = adapter.propsController ? adapter.propsController(this) : null;
  }

  private _placeholder: Texture | null = null;
  private _placeholderPromise: Promise<Texture> | null = null;

  unknownEntities: Set<Entity3d> = new Set<Entity3d>();

  override onSpawned(world: ThreeGgWorld) {
    super.onSpawned(world);
    this.hideUnknownEntities$.pipe(distinctUntilChanged(), takeUntil(this._onRemoved$)).subscribe(hide => {
      for (const e of this.unknownEntities) {
        e.visible = !hide;
      }
    });
  }

  // Marks an entity as "unknown" (e.g. a prop whose model/texture couldn't be loaded): it follows the
  // global "hide hidden fields" toggle
  markUnknown(entity: TrackEntity) {
    this.unknownEntities.add(entity as Entity3d);
    entity.visible = !this.hideUnknownEntities$.getValue();
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
        this.setupTerrainTexture(texture);
        return texture;
      });
    }
    return this._placeholderTerrainPromise;
  }

  private setupTerrainTexture(texture: Texture) {
    (this.adapter.setupTerrainTexture || setupTerrainTextureDefault)(texture);
  }

  protected override async loadChunk(
    node: MapGraphNodeType,
  ): Promise<[TrackEntity[], LoadResultWithProps<TypeDocOf<ThreeGgWorld>>]> {
    const object = await this.objLoader.loadAsync(node.path + '.obj');
    object.position.set(node.position.x, node.position.y, node.position.z);
    object.traverse((child: any) => {
      if (child instanceof Mesh) {
        child.material = this.getTerrainMaterial(meshTextureName(child));
      }
    });
    const props = await this.loadChunkProps(node);
    const entity: TrackEntity = new Entity3d({
      object3D: new ThreeDisplayObjectComponent(object),
    });
    this.addChildren(entity, ...props);
    this.loaded.set(node, [entity, ...props]);
    return [[entity, ...props], null!];
  }

  private async loadChunkProps(node: MapGraphNodeType): Promise<TrackEntity[]> {
    const extraPath = `${node.path}_extra.json`;
    if (!this.propsController || !this.serializedFiles.includes(extraPath)) {
      return [];
    }
    let dummies: GgDummy[];
    try {
      dummies = ((await (await fetch(extraPath)).json()).dummies || []).map(extraJsonDummyToGgDummy);
    } catch (err) {
      console.warn(`Could not load props of ${node.path}`, err);
      return [];
    }
    const props = await this.propsController.spawnChunkProps(dummies, node.position);
    for (const prop of props) {
      if (prop.isUnknown) {
        this.markUnknown(prop.entity as TrackEntity);
      }
    }
    return props.map(p => p.entity as TrackEntity);
  }

  // `TrackPropsAssets`: models are the OBJ files of the converter
  loadModel(dir: string, withMaterials: boolean): Promise<Object3D | null> {
    const key = `${dir}|${withMaterials}`;
    if (!this.models.has(key)) {
      this.models.set(
        key,
        (async () => {
          const loader = new OBJLoader();
          if (withMaterials) {
            try {
              const materials = await new MTLLoader().loadAsync(`${dir}/material.mtl`);
              materials.preload();
              loader.setMaterials(materials);
            } catch (err) {
              // a model without materials
            }
          }
          return loader.loadAsync(`${dir}/geometry.obj`);
        })().catch(err => {
          console.warn(`Could not load model ${dir}`, err);
          return null;
        }),
      );
    }
    return this.models.get(key)!.then(model => (model ? model.clone() : null));
  }

  async loadTexture(path: string): Promise<Texture | null> {
    return this.textureLoader.loadAsync(path).catch(() => null);
  }

  placeholderModel(): Object3D {
    const material = new MeshBasicMaterial();
    this.getPlaceholderTexture().then(texture => {
      material.map = texture;
      material.needsUpdate = true;
    });
    return new Mesh(new SphereGeometry(5), material);
  }

  placeholderTexture(): Promise<Texture> {
    return this.getPlaceholderTexture();
  }

  protected override disposeChunk(node: MapGraphNodeType) {
    for (const c of this.loaded.get(node) || []) {
      this.unknownEntities.delete(c as Entity3d);
    }
    super.disposeChunk(node);
  }

  getTerrainMaterial(matId: string): Material {
    if (!this.terrainMaterials[matId]) {
      this.terrainMaterials[matId] = new MeshBasicMaterial({
        side: DoubleSide,
        transparent: true,
        visible: false,
        alphaTest: this.adapter.terrainAlphaTest || 0,
      });
      const applyTexture = (texture: Texture) => {
        this.terrainMaterials[matId].map = texture;
        this.terrainMaterials[matId].needsUpdate = true;
        this.terrainMaterials[matId].visible = true;
      };
      if (this.textureArchivePath) {
        this.textureLoader
          .loadAsync(`${this.textureArchivePath}/${matId}.png`)
          .then(texture => {
            this.setupTerrainTexture(texture);
            applyTexture(texture);
          })
          .catch(() => {
            console.warn(`Problem with loading terrain material ${matId}`);
            this.getPlaceholderTerrainTexture().then(applyTexture);
          });
      } else {
        this.getPlaceholderTerrainTexture().then(applyTexture);
      }
    }
    return this.terrainMaterials[matId];
  }
}
