import {
  Entity3d,
  GgWorld,
  LoadResultWithProps,
  MapGraph,
  MapGraph3dEntity,
  MapGraphNodeType,
} from '@gg-web-engine/core';
import { BehaviorSubject, distinctUntilChanged, takeUntil } from 'rxjs';
import { DoubleSide, Material, Mesh, MeshBasicMaterial, Object3D, RepeatWrapping, Texture, TextureLoader } from 'three';
import { ThreeDisplayObjectComponent, ThreeGgWorld } from '@gg-web-engine/three';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { setupNfs1Texture } from '../../common/obj-viewer/obj-viewer.component';
import { Resource } from '../../types';
import { TrackMapAdapter } from './track-map-adapters';

// TODO use this from gg-web-engine after next release
export type TypeDocOf<W extends GgWorld<any, any>> =
  W extends GgWorld<infer D, infer R, infer TypeDoc> ? TypeDoc : never;

export type TrackEntity = Entity3d<TypeDocOf<ThreeGgWorld>>;

// Meshes of the serialized chunks and props are named "<name>_<texture name>"
export function meshTextureName(mesh: Object3D): string {
  const name: string = mesh.userData['name'] || mesh.name;
  return name.substring(name.lastIndexOf('_') + 1).split('.')[0];
}

function setupTerrainTextureDefault(texture: Texture) {
  texture.wrapS = RepeatWrapping;
  texture.wrapT = RepeatWrapping;
  setupNfs1Texture(texture);
}

// Track terrain streamed as OBJ chunks along a MapGraph, textured from `<textureArchivePath>/<name>.png`: a texture
// archive (QFS/FAM) serialized there, or textures the track serializer wrote next to the chunks. Chunk extras (props)
// come from the adapter.
export class TrackMapWorldEntity extends MapGraph3dEntity<TypeDocOf<ThreeGgWorld>> {
  public readonly textureLoader = new TextureLoader();
  private readonly terrainMaterials: { [key: string]: MeshBasicMaterial } = {};
  private readonly objLoader = new OBJLoader();

  constructor(
    public override readonly mapGraph: MapGraph,
    public readonly textureArchivePath: string | null,
    private readonly hideUnknownEntities$: BehaviorSubject<boolean>,
    public readonly adapter: TrackMapAdapter,
    public readonly resource: Resource,
    public readonly isOpenedTrack: boolean,
    // Files written by the track serializer (chunks and what comes with them)
    public readonly serializedFiles: string[] = [],
  ) {
    super(mapGraph, { loadDepth: adapter.loadDepth ?? 40, inertia: 2 });
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
    const chunkIndex = +node.path.split('_')[node.path.split('_').length - 1];
    const props = this.adapter.loadChunkProps ? await this.adapter.loadChunkProps(this, chunkIndex, node) : [];
    const entity: TrackEntity = new Entity3d({
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
