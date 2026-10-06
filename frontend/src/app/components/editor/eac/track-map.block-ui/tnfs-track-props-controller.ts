import {
  ClampToEdgeWrapping,
  DoubleSide,
  Group,
  Material,
  Mesh,
  MeshBasicMaterial,
  Object3D,
  PlaneGeometry,
  Texture,
} from 'three';
import { GgDummy, Point2, Point3 } from '@gg-web-engine/core';
import { takeUntil } from 'rxjs';
import { setupNfs1Texture } from '../../common/obj-viewer/obj-viewer.component';
import { TrackProp, TrackPropEntity, TrackPropsAssets, TrackPropsController } from './track-props-controller';

export enum TnfsPropType {
  ThreeModel = 'model',
  Bitmap = 'bitmap',
  TwoSidedBitmap = 'two_sided_bitmap',
}

/**
 * Props of a TNFS track (TRI). Models and bitmaps come from the track's FAM file, exported by the converter to
 * `famPath`. A prop dummy has fields:
 * - `is_prop`: true
 * - `type`: "model", "bitmap" or "two_sided_bitmap"
 * - `model_ref_id` (model): the FAM prop, exported to folder `<famPath>/props/<model_ref_id>/0`, with its own textures
 * - `texture`, `width`, `height` (bitmaps): a vertical plane standing on the dummy position. `texture` is ";"-separated
 *   textures `<famPath>/foreground/<texture>.png`: frames of animation, switched every `animation_interval` seconds
 * - `back_texture`, `back_width` (two-sided bitmap): a second plane, perpendicular to the first one at its right edge
 * - `road_index`: road spline point the prop is placed relative to
 *
 * A mirrored track (`mirrored`, X axis flipped as the terrain chunks of a mirrored track are) mirrors props too
 */
export class TnfsTrackPropsController extends TrackPropsController {
  constructor(
    assets: TrackPropsAssets,
    public readonly famPath: string,
    public readonly mirrored: boolean = false,
  ) {
    super(assets, `${famPath}/props`);
  }

  protected override async spawnProp(dummy: GgDummy, chunkPosition: Point3): Promise<TrackProp | null> {
    if (this.mirrored) {
      dummy = {
        ...dummy,
        position: { x: -dummy.position.x, y: dummy.position.y, z: dummy.position.z },
        // mirrors rotation across YZ plane
        rotation: { x: dummy.rotation.x, y: -dummy.rotation.y, z: -dummy.rotation.z, w: dummy.rotation.w },
      };
    }
    const mirrorX = this.mirrored ? -1 : 1;
    if (dummy.type == TnfsPropType.ThreeModel) {
      let isUnknown = false;
      let object = await this.assets.loadModel(`${this.propsPath}/${dummy.model_ref_id}/0`, true);
      if (object) {
        setupNfs1ModelMaterials(object);
        object.scale.setX(mirrorX);
      } else if (this.assets.placeholderModel) {
        object = this.assets.placeholderModel();
        isUnknown = true;
      } else {
        return null;
      }
      return { dummy, entity: this.createEntity(object, dummy, chunkPosition), isUnknown };
    } else if (dummy.type == TnfsPropType.Bitmap || dummy.type == TnfsPropType.TwoSidedBitmap) {
      const object: Object3D = new Group();
      const entity = this.createEntity(object, dummy, chunkPosition);
      const [plane, isUnknown] = await this.loadTexturePlane(
        entity,
        dummy.texture,
        { x: dummy.width, y: dummy.height },
        dummy.animation_interval,
      );
      if (!plane) {
        return null;
      }
      plane.scale.setX(mirrorX);
      object.add(plane);
      let isBackUnknown = false;
      if (dummy.type == TnfsPropType.TwoSidedBitmap) {
        const [plane2, isPlane2Unknown] = await this.loadTexturePlane(
          entity,
          dummy.back_texture,
          { x: dummy.back_width, y: dummy.height },
          dummy.animation_interval,
        );
        if (plane2) {
          plane2.rotateY((mirrorX * Math.PI) / 2);
          plane2.position.x = (mirrorX * dummy.width) / 2;
          plane2.position.y = dummy.back_width / 2;
          plane2.scale.setX(mirrorX);
          object.add(plane2);
        }
        isBackUnknown = isPlane2Unknown || !plane2;
      }
      return { dummy, entity, isUnknown: isUnknown || isBackUnknown };
    }
    return null;
  }

  // A vertical plane with a FAM "foreground" bitmap; several textures make an animation
  private async loadTexturePlane(
    entity: TrackPropEntity,
    texture: string,
    size: Point2,
    animationInterval: number,
  ): Promise<[Object3D | null, boolean]> {
    let isUnknown = false;
    const maps = await Promise.all(
      `${texture}`.split(';').map(async t => {
        const map = await this.assets.loadTexture(`${this.famPath}/foreground/${t}.png`);
        if (map) {
          return map;
        }
        isUnknown = true;
        return this.assets.placeholderTexture ? this.assets.placeholderTexture() : null;
      }),
    );
    if (maps.some(m => !m)) {
      return [null, true];
    }
    const materials: Material[] = (maps as Texture[]).map(map => {
      setupNfs1Texture(map);
      return new MeshBasicMaterial({ map, alphaTest: 0.5, transparent: true, side: DoubleSide });
    });
    const plane = new Mesh(new PlaneGeometry(size.x, size.y), materials[0]);
    plane.rotateX(Math.PI / 2);
    plane.position.set(0, 0, size.y / 2);
    if (materials.length > 1) {
      const interval = 1000 * (animationInterval && !isNaN(+animationInterval) ? +animationInterval : 0.25);
      entity.tick$.pipe(takeUntil(entity.onRemoved$)).subscribe(([elapsed]) => {
        plane.material = materials[Math.floor(elapsed / interval) % materials.length];
      });
    }
    return [plane, isUnknown];
  }
}

// FAM models are unlit, with alpha-tested textures
function setupNfs1ModelMaterials(object: Object3D) {
  object.traverse(o => {
    if (!(o instanceof Mesh)) {
      return;
    }
    const materials = (o.material instanceof Array ? o.material : [o.material]).map((material: Material) => {
      const basic =
        material instanceof MeshBasicMaterial
          ? material
          : new MeshBasicMaterial({ map: (material as any).map || null, side: material.side });
      basic.transparent = true;
      basic.alphaTest = 0.5;
      if (basic.map) {
        basic.map.wrapS = ClampToEdgeWrapping;
        basic.map.wrapT = ClampToEdgeWrapping;
        setupNfs1Texture(basic.map);
        basic.map.needsUpdate = true;
      }
      return basic;
    });
    o.material = materials.length > 1 ? materials : materials[0];
  });
}
