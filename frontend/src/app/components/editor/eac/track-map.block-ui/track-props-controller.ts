import { Material, Mesh, Object3D, Texture } from 'three';
import { Entity3d, GgDummy, Pnt3, Point3, Point4, Qtrn } from '@gg-web-engine/core';
import { ThreeDisplayObjectComponent, ThreeTypeDoc } from '@gg-web-engine/three';
import { takeUntil } from 'rxjs';

// Track props controllers spawn and animate the props of a track exported by nfs-resources-converter without
// "Add props to obj": every prop is a dummy (empty object) in the meta of a terrain chunk ("terrain_chunk_<i>.meta"
// of the gg-web-engine export, "terrain_chunk_<i>_extra.json" next to the OBJ), its position is relative to the
// chunk. The controllers only depend on three.js and gg-web-engine: files are loaded by the app through
// `TrackPropsAssets`, so the same controllers render tracks in the converter GUI and in nfs-web.

// Files exported by the converter, loaded by the app that renders the track
export interface TrackPropsAssets {
  // A model exported by the converter into a folder: "body.glb" (gg-web-engine export) or "geometry.obj" +
  // "material.mtl". Returns a new object (it may share geometry and materials with other copies), null if the model
  // cannot be loaded. Without `withMaterials` the controller replaces the materials, so they may be skipped
  loadModel(dir: string, withMaterials: boolean): Promise<Object3D | null>;
  // An image, e.g. a PNG texture exported by the converter. Null if it cannot be loaded
  loadTexture(path: string): Promise<Texture | null>;
  // Material of the track texture `textureName`: meshes of terrain chunks and props are named "<name>_<texture>"
  getTerrainMaterial(textureName: string): Material;
  // Stands in for a model or a texture which cannot be loaded (the prop is then reported as unknown). Without them
  // such a prop is not spawned
  placeholderModel?(): Object3D;
  placeholderTexture?(): Promise<Texture>;
}

export type TrackPropEntity = Entity3d<ThreeTypeDoc>;

export interface TrackProp {
  dummy: GgDummy;
  entity: TrackPropEntity;
  // A file of the prop could not be loaded, or the converter is not sure the prop looks like this in the game
  isUnknown: boolean;
}

// One keyframe of a prop animation, absolute position
interface TrackPropKeyframe {
  position: Point3;
  rotation: Point4;
}

// Meshes of the exported chunks and props are named "<name>_<texture name>"
export function meshTextureName(mesh: Object3D): string {
  const name: string = mesh.userData['name'] || mesh.name;
  return name.substring(name.lastIndexOf('_') + 1).split('.')[0];
}

// [w, x, y, z], as the converter writes quaternions in JSON (Blender order)
function quaternionFromWxyz(q: number[] | undefined): Point4 {
  return q ? { x: q[1], y: q[2], z: q[3], w: q[0] } : Qtrn.O;
}

/**
 * Props of NFS2 (TRK), NFS3 and NFS4 (FRD) tracks. A prop dummy has fields:
 * - `is_prop`: true
 * - `type`: "model"
 * - `model_ref_id`: the model, exported once to folder `<propsPath>/<model_ref_id>` (shared by all props using it).
 *   It has no materials of its own: its meshes are named "<model>__<texture>" and get the track textures
 * - `animation` (optional): JSON `{"frame_duration": <seconds>, "frames": [{"position": [x, y, z],
 *   "quaternion": [w, x, y, z]}, ...]}`, positions in the same coordinates as the dummy position. The prop loops
 *   through the keyframes, the first one is where the dummy is
 * - `is_unknown` (optional): the converter is not sure the prop looks like this in the game
 */
export class TrackPropsController {
  constructor(
    protected readonly assets: TrackPropsAssets,
    // folder with prop models: "<track export>/props"
    protected readonly propsPath: string,
  ) {}

  // Spawns props of a terrain chunk: entities are positioned in the world, the caller adds them to it (e.g. as
  // children of the map entity, so they are removed with the chunk)
  async spawnChunkProps(dummies: GgDummy[], chunkPosition: Point3): Promise<TrackProp[]> {
    const props = await Promise.all(
      dummies.filter(d => d.is_prop).map(d => this.spawnProp(d, chunkPosition).catch(() => null)),
    );
    return props.filter(p => !!p) as TrackProp[];
  }

  protected async spawnProp(dummy: GgDummy, chunkPosition: Point3): Promise<TrackProp | null> {
    if ((dummy.type || 'model') !== 'model' || dummy.model_ref_id === undefined) {
      return null;
    }
    let isUnknown = !!dummy.is_unknown;
    let object = await this.assets.loadModel(`${this.propsPath}/${dummy.model_ref_id}`, false);
    if (object) {
      this.applyTerrainMaterials(object);
    } else if (this.assets.placeholderModel) {
      object = this.assets.placeholderModel();
      isUnknown = true;
    } else {
      return null;
    }
    const entity = this.createEntity(object, dummy, chunkPosition);
    if (dummy.animation) {
      this.animateKeyframes(entity, chunkPosition, JSON.parse(dummy.animation));
    }
    return { dummy, entity, isUnknown };
  }

  protected applyTerrainMaterials(object: Object3D) {
    object.traverse(o => {
      if (o instanceof Mesh) {
        o.material = this.assets.getTerrainMaterial(meshTextureName(o));
      }
    });
  }

  protected createEntity(object: Object3D, dummy: GgDummy, chunkPosition: Point3): TrackPropEntity {
    const entity: TrackPropEntity = new Entity3d({ object3D: new ThreeDisplayObjectComponent(object) });
    entity.position = Pnt3.add(chunkPosition, dummy.position);
    entity.rotation = dummy.rotation;
    return entity;
  }

  // Loops through the keyframes, interpolating between them
  protected animateKeyframes(entity: TrackPropEntity, chunkPosition: Point3, animation: any) {
    const frames: TrackPropKeyframe[] = (animation.frames || []).map((f: any) => ({
      position: Pnt3.add(chunkPosition, { x: f.position[0], y: f.position[1], z: f.position[2] }),
      rotation: quaternionFromWxyz(f.quaternion),
    }));
    if (frames.length < 2) {
      return;
    }
    const frameDuration = 1000 * (animation.frame_duration || 1 / 64);
    entity.tick$.pipe(takeUntil(entity.onRemoved$)).subscribe(([elapsed]) => {
      const t = elapsed / frameDuration;
      const i = Math.floor(t) % frames.length;
      const next = frames[(i + 1) % frames.length];
      const k = t - Math.floor(t);
      entity.position = Pnt3.lerp(frames[i].position, next.position, k);
      entity.rotation = Qtrn.slerp(frames[i].rotation, next.rotation, k);
    });
  }
}
