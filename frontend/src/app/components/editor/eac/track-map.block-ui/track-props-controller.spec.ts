import { Group, Material, Mesh, MeshBasicMaterial, Object3D, PlaneGeometry, Texture } from 'three';
import { GgDummy } from '@gg-web-engine/core';
import { TrackPropsAssets, TrackPropsController } from './track-props-controller';
import { TnfsTrackPropsController } from './tnfs-track-props-controller';

class FakeAssets implements TrackPropsAssets {
  loadedModels: string[] = [];
  loadedTextures: string[] = [];
  materials: { [name: string]: Material } = {};

  async loadModel(dir: string): Promise<Object3D | null> {
    this.loadedModels.push(dir);
    if (dir.endsWith('missing')) {
      return null;
    }
    const group = new Group();
    const mesh = new Mesh(new PlaneGeometry(1, 1), new MeshBasicMaterial());
    mesh.name = 'model__0145';
    group.add(mesh);
    return group;
  }

  async loadTexture(path: string): Promise<Texture | null> {
    this.loadedTextures.push(path);
    return new Texture();
  }

  getTerrainMaterial(textureName: string): Material {
    return (this.materials[textureName] ||= new MeshBasicMaterial());
  }
}

function dummy(props: any): GgDummy {
  return {
    name: 'prop_0',
    position: { x: 1, y: 2, z: 3 },
    rotation: { x: 0, y: 0, z: 0, w: 1 },
    is_prop: true,
    ...props,
  };
}

describe('TrackPropsController', () => {
  it('spawns models with track materials, relative to the chunk', async () => {
    const assets = new FakeAssets();
    const props = await new TrackPropsController(assets, 'track/props').spawnChunkProps(
      [dummy({ type: 'model', model_ref_id: 'xobj_1' }), { ...dummy({}), is_prop: false }],
      { x: 10, y: 20, z: 30 },
    );
    expect(props.length).toBe(1);
    expect(assets.loadedModels).toEqual(['track/props/xobj_1']);
    expect(props[0].entity.position).toEqual({ x: 11, y: 22, z: 33 });
    expect(props[0].isUnknown).toBeFalse();
    let material: Material | null = null;
    props[0].entity.object3D!.nativeMesh.traverse(o => {
      if (o instanceof Mesh) {
        material = o.material;
      }
    });
    expect(material!).toBe(assets.materials['0145']);
  });

  it('skips props without models, unless there is a placeholder', async () => {
    const assets = new FakeAssets();
    const controller = new TrackPropsController(assets, 'props');
    const dummies = [dummy({ type: 'model', model_ref_id: 'missing' })];
    expect((await controller.spawnChunkProps(dummies, { x: 0, y: 0, z: 0 })).length).toBe(0);
    (assets as TrackPropsAssets).placeholderModel = () => new Group();
    const props = await controller.spawnChunkProps(dummies, { x: 0, y: 0, z: 0 });
    expect(props.length).toBe(1);
    expect(props[0].isUnknown).toBeTrue();
  });

  it('plays keyframe animation in a loop', async () => {
    const animation = {
      frame_duration: 0.5,
      frames: [
        { position: [1, 2, 3], quaternion: [1, 0, 0, 0] },
        { position: [3, 2, 3], quaternion: [1, 0, 0, 0] },
      ],
    };
    const [prop] = await new TrackPropsController(new FakeAssets(), 'props').spawnChunkProps(
      [dummy({ type: 'model', model_ref_id: 'plane', animation: JSON.stringify(animation) })],
      { x: 100, y: 0, z: 0 },
    );
    prop.entity.tick$.next([250, 16]);
    expect(prop.entity.position.x).toBeCloseTo(102);
    prop.entity.tick$.next([750, 16]);
    expect(prop.entity.position.x).toBeCloseTo(102);
    prop.entity.tick$.next([1000, 16]);
    expect(prop.entity.position.x).toBeCloseTo(101);
  });
});

describe('TnfsTrackPropsController', () => {
  it('spawns FAM models and two-sided bitmaps', async () => {
    const assets = new FakeAssets();
    const controller = new TnfsTrackPropsController(assets, 'fam');
    const props = await controller.spawnChunkProps(
      [
        dummy({ type: 'model', model_ref_id: 3 }),
        dummy({
          type: 'two_sided_bitmap',
          texture: '0/0400',
          back_texture: '0/0800',
          width: 4,
          back_width: 2,
          height: 3,
        }),
      ],
      { x: 0, y: 0, z: 0 },
    );
    expect(assets.loadedModels).toEqual(['fam/props/3/0']);
    expect(assets.loadedTextures).toEqual(['fam/foreground/0/0400.png', 'fam/foreground/0/0800.png']);
    expect(props.length).toBe(2);
    expect(props[1].entity.object3D!.nativeMesh.children.length).toBe(2);
  });

  it('mirrors props of a mirrored track', async () => {
    const [prop] = await new TnfsTrackPropsController(new FakeAssets(), 'fam', true).spawnChunkProps(
      [dummy({ type: 'bitmap', texture: '0/0400;0/0500', width: 4, height: 3, animation_interval: 0.5 })],
      { x: 0, y: 0, z: 0 },
    );
    expect(prop.entity.position).toEqual({ x: -1, y: 2, z: 3 });
    const plane = prop.entity.object3D!.nativeMesh.children[0] as Mesh;
    expect(plane.scale.x).toBe(-1);
    const firstFrame = plane.material;
    prop.entity.tick$.next([600, 16]);
    expect(plane.material).not.toBe(firstFrame);
  });
});
