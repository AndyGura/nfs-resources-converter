import { Entity3d, MapGraphNodeType, Pnt3, Point3, Point4, Qtrn } from '@gg-web-engine/core';
import { takeUntil } from 'rxjs';
import { Mesh, Object3D } from 'three';
import { ThreeDisplayObjectComponent } from '@gg-web-engine/three';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { meshTextureName, TrackEntity, TrackMapWorldEntity } from './track-map-world.entity';

// Animation delay units per second of NFS2/NFS3 animated props (assumed, not confirmed)
const ANIMATION_DELAY_UNITS_PER_SECOND = 64;

interface PropKeyframe {
  position: Point3;
  rotation: Point4;
}

const modelCache = new WeakMap<TrackMapWorldEntity, Map<string, Promise<Object3D | null>>>();

// [w, x, y, z] as written by the serializer
function toQtrn(q: number[] | undefined): Point4 {
  return q ? { x: q[1], y: q[2], z: q[3], w: q[0] } : Qtrn.O;
}

function toPoint(p: number[]): Point3 {
  return { x: p[0], y: p[1], z: p[2] };
}

function loadModel(map: TrackMapWorldEntity, path: string): Promise<Object3D | null> {
  let cache = modelCache.get(map);
  if (!cache) {
    cache = new Map();
    modelCache.set(map, cache);
  }
  if (!cache.has(path)) {
    cache.set(
      path,
      new OBJLoader().loadAsync(path).catch(err => {
        console.warn(`Could not load prop model ${path}`, err);
        return null;
      }),
    );
  }
  return cache.get(path)!;
}

// Props of NFS2 (TRK) and NFS3 (FRD) tracks, written by the track serializer: dummies in "terrain_chunk_<i>_extra.json"
// with a position relative to the chunk, a rotation quaternion and a model ("props/<model_ref_id>.obj" next to the
// chunks). An animated prop has an "animation" property: JSON with keyframes in the same coordinates and delay between
// them. Props use terrain materials, picked by mesh name like the chunk meshes. A prop with "is_unknown" property is
// hidden unless hidden fields are shown
export async function loadSerializedChunkProps(
  map: TrackMapWorldEntity,
  chunkIndex: number,
  node: MapGraphNodeType,
): Promise<TrackEntity[]> {
  const extraPath = `${node.path}_extra.json`;
  if (!map.serializedFiles.includes(extraPath)) {
    return [];
  }
  let extra: any;
  try {
    const response = await fetch(extraPath);
    if (!response.ok) {
      return [];
    }
    extra = await response.json();
  } catch (err) {
    return [];
  }
  const dir = node.path.substring(0, node.path.lastIndexOf('/') + 1);
  const dummies = (extra.dummies || []).filter((d: any) => d.properties?.is_prop && d.properties?.model_ref_id);
  const props = await Promise.all(dummies.map((d: any) => loadProp(map, dir, node.position, d)));
  return props.filter(p => !!p) as TrackEntity[];
}

async function loadProp(
  map: TrackMapWorldEntity,
  dir: string,
  chunkPosition: Point3,
  dummy: any,
): Promise<TrackEntity | null> {
  const model = await loadModel(map, `${dir}props/${dummy.properties.model_ref_id}.obj`);
  if (!model) {
    return null;
  }
  const object = model.clone();
  object.traverse(x => {
    if (x instanceof Mesh) {
      x.material = map.getTerrainMaterial(meshTextureName(x));
    }
  });
  const entity: TrackEntity = new Entity3d({ object3D: new ThreeDisplayObjectComponent(object) });
  entity.position = Pnt3.add(chunkPosition, toPoint(dummy.position));
  entity.rotation = toQtrn(dummy.quaternion);
  if (dummy.properties.animation) {
    animateProp(entity, chunkPosition, JSON.parse(dummy.properties.animation));
  }
  if (dummy.properties.is_unknown) {
    map.markUnknown(entity);
  }
  return entity;
}

// Loops through the keyframes, interpolating between them
function animateProp(entity: TrackEntity, chunkPosition: Point3, animation: any) {
  const frames: PropKeyframe[] = (animation.frames || []).map((f: any) => ({
    position: Pnt3.add(chunkPosition, toPoint(f.position)),
    rotation: toQtrn(f.quaternion),
  }));
  if (frames.length < 2) {
    return;
  }
  const frameDuration = (1000 * Math.max(animation.delay || 1, 1)) / ANIMATION_DELAY_UNITS_PER_SECOND;
  entity.tick$.pipe(takeUntil(entity.onRemoved$)).subscribe(([elapsed]) => {
    const t = elapsed / frameDuration;
    const i = Math.floor(t) % frames.length;
    const next = frames[(i + 1) % frames.length];
    const k = t - Math.floor(t);
    entity.position = Pnt3.lerp(frames[i].position, next.position, k);
    entity.rotation = Qtrn.slerp(frames[i].rotation, next.rotation, k);
  });
}
