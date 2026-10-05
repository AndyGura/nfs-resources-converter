import { createInlineTickController, Entity3d, Pnt3, Point2, Qtrn } from '@gg-web-engine/core';
import { throttleTime } from 'rxjs';
import {
  ClampToEdgeWrapping,
  DoubleSide,
  Group,
  Material,
  Mesh,
  MeshBasicMaterial,
  Object3D,
  PlaneGeometry,
} from 'three';
import { ThreeDisplayObjectComponent } from '@gg-web-engine/three';
import { OBJLoader } from 'three/examples/jsm/loaders/OBJLoader.js';
import { MTLLoader } from 'three/examples/jsm/loaders/MTLLoader.js';
import { setupNfs1Texture } from '../../common/obj-viewer/obj-viewer.component';
import { TrackEntity, TrackMapWorldEntity } from './track-map-world.entity';

export enum MapPropType {
  ThreeModel = 'model',
  Bitmap = 'bitmap',
  TwoSidedBitmap = 'two_sided_bitmap',
}

// Props (3D models and 2D bitmaps from the track's FAM file) placed on a TNFS TRI track chunk.
// Each chunk spans 4 road spline points; a prop is positioned relative to its spline point.
export async function loadTnfsChunkProps(map: TrackMapWorldEntity, chunkIndex: number): Promise<TrackEntity[]> {
  const data = map.resource.data;
  const propInstances = (data.props || [])
    .filter((x: any) => x.road_point_idx >= chunkIndex * 4 && x.road_point_idx < (chunkIndex + 1) * 4)
    .map((x: any) => ({
      ...x,
      ...data.prop_descr[x.prop_descr_idx],
      position: Pnt3.add(
        { x: x.position.x, y: x.position.z, z: x.position.y },
        {
          x: data.road_spline[x.road_point_idx].position.x,
          y: data.road_spline[x.road_point_idx].position.z,
          z: data.road_spline[x.road_point_idx].position.y,
        },
      ),
      rotation: Qtrn.fromAngle(Pnt3.nZ, x.rotation + data.road_spline[x.road_point_idx].orientation),
    }));
  return (await Promise.all(propInstances.map((x: any) => loadProp(map, x)))).filter(p => !!p) as TrackEntity[];
}

async function loadProp(map: TrackMapWorldEntity, dummy: any): Promise<TrackEntity | null> {
  const famPath = map.textureArchivePath;
  if (dummy.type == MapPropType.ThreeModel) {
    let isUnknown = false;
    let object: ThreeDisplayObjectComponent;
    try {
      if (!famPath) throw new Error();
      const mtlLoader = new MTLLoader();
      const objLoader = new OBJLoader();
      const mtl = await mtlLoader.loadAsync(`${famPath}/props/${dummy.data.data.resource_id}/0/material.mtl`);
      mtl.preload();
      objLoader.setMaterials(mtl);
      object = new ThreeDisplayObjectComponent(
        await objLoader.loadAsync(`${famPath}/props/${dummy.data.data.resource_id}/0/geometry.obj`),
      );
    } catch (err) {
      isUnknown = true;
      object = map.world!.visualScene!.factory.createPrimitive(
        { shape: 'SPHERE', radius: 5 },
        { diffuse: await map.getPlaceholderTexture() },
      ) as ThreeDisplayObjectComponent;
    }
    object.nativeMesh.traverse(x => {
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
    const prop: TrackEntity = new Entity3d({ object3D: object });
    prop.position = dummy.position;
    prop.rotation = dummy.rotation;
    if (isUnknown) {
      map.markUnknown(prop);
    }
    map.world!.addEntity(prop);
    return prop;
  } else if (dummy.type == MapPropType.Bitmap || dummy.type == MapPropType.TwoSidedBitmap) {
    const textureIds = (resId: number, framesAmount: number) =>
      new Array(framesAmount)
        .fill(null)
        .map((_, i) =>
          map.isOpenedTrack
            ? `${Math.floor(resId / 4) + i}/0000`
            : `0/${(Math.floor(resId / 4) + i).toString().padStart(2, '0')}00`,
        );

    const object: Object3D = new Group();
    const [plane, isUnknown] = await loadTexturePlane(
      map,
      textureIds(dummy.data.data.resource_id, dummy.flags.is_animated ? dummy.data.data.frame_count : 1),
      { x: dummy.data.data.width, y: dummy.data.data.height },
      dummy.data.data.animation_interval,
    );
    object.add(plane);
    if (dummy.type == MapPropType.TwoSidedBitmap) {
      const [plane2] = await loadTexturePlane(
        map,
        textureIds(dummy.data.data.resource_id_2, 1),
        { x: dummy.data.data.width_2, y: dummy.data.data.height },
        dummy.data.data.animation_interval,
      );
      plane2.rotateY(Math.PI / 2);
      plane2.position.x = dummy.data.data.width / 2;
      plane2.position.y = dummy.data.data.width_2 / 2;
      object.add(plane2);
    }
    const entity: TrackEntity = new Entity3d({ object3D: new ThreeDisplayObjectComponent(object) });
    entity.position = dummy.position;
    entity.rotation = dummy.rotation;
    if (isUnknown) {
      map.markUnknown(entity);
    }
    return entity;
  }
  return null;
}

// A vertical plane with a FAM "foreground" bitmap; several textures make an animation
async function loadTexturePlane(
  map: TrackMapWorldEntity,
  textures: string[],
  size: Point2,
  animationInterval: number,
): Promise<[Object3D, boolean]> {
  const famPath = map.textureArchivePath;
  const placeholder = await map.getPlaceholderTexture();
  let isUnknown = false;
  let maps = [];
  if (!famPath) {
    isUnknown = true;
    maps = textures.map(() => placeholder);
  } else {
    maps = await Promise.all(
      textures.map(t =>
        map.textureLoader.loadAsync(`${famPath}/foreground/${t}.png`).catch(() => {
          isUnknown = true;
          return placeholder;
        }),
      ),
    );
  }
  const materials = maps.map(texture => {
    setupNfs1Texture(texture);
    return new MeshBasicMaterial({ map: texture, alphaTest: 0.5, transparent: true, side: DoubleSide });
  });
  const plane = new Mesh(new PlaneGeometry(size.x, size.y), materials[0]);
  plane.rotateX(Math.PI / 2);
  plane.position.set(0, 0, size.y / 2);
  if (materials.length > 1) {
    let i = -1;
    // TODO where to unsubscribe?
    createInlineTickController(map.world!)
      .pipe(throttleTime(animationInterval && !isNaN(+animationInterval) ? +animationInterval * 1000 : 250))
      .subscribe(() => {
        i = (i + 1) % materials.length;
        plane.material = materials[i];
      });
  }
  return [plane, isUnknown];
}
