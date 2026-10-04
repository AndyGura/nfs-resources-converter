import { Material, Mesh, MeshBasicMaterial, MeshPhongMaterial, Object3D, Texture } from 'three';
import { setupNfs1Texture } from '../../common/obj-viewer/obj-viewer.component';
import { sleep } from '../../../../utils/sleep';
import { recolorImageSmart } from '../../../../utils/recolor-image';

// NFS5 car exterior texture pages are semi-transparent: the alpha channel says how much of the car paint color
// shows through the texture
const PAINTED_MATERIALS = ['page_0', 'page_1'];

export class CrpCarMeshController {
  // original/patched texture pairs
  textures: [Texture, Texture][] = [];

  private _color: number = 0xffffff;
  get color(): number {
    return this._color;
  }

  set color(value: number) {
    if (value === this._color) return;
    this._color = value;
    this.recolorCar().then();
  }

  get hasPaintedTextures(): boolean {
    return this.textures.length > 0;
  }

  constructor(private readonly mesh: Object3D) {
    const patches: Map<Texture, Texture> = new Map();
    mesh.traverse(o => {
      if (!(o instanceof Mesh)) {
        return;
      }
      const materials: Material[] = o.material instanceof Array ? o.material : [o.material];
      for (const m of materials) {
        if (
          !(m instanceof MeshBasicMaterial || m instanceof MeshPhongMaterial) ||
          !m.map ||
          !PAINTED_MATERIALS.includes(m.name)
        ) {
          continue;
        }
        let patch = patches.get(m.map);
        if (!patch) {
          patch = new Texture(document.createElement('img'));
          patch.flipY = m.map.flipY;
          patch.wrapS = m.map.wrapS;
          patch.wrapT = m.map.wrapT;
          setupNfs1Texture(patch);
          patches.set(m.map, patch);
        }
        m.map = patch;
        m.needsUpdate = true;
      }
    });
    this.textures = Array.from(patches.entries());
    this.recolorCar().then();
  }

  async recolorCar() {
    const [red, green, blue] = [this.color >> 16, (this.color >> 8) & 0xff, this.color & 0xff];
    for (const [ot, dt] of this.textures) {
      for (let i = 100; i > 0; i--) {
        const img = ot.source.data as HTMLImageElement | undefined;
        if (img && img.complete && img.naturalWidth > 0) break;
        await sleep(50);
      }
      const target = dt.source.data as HTMLImageElement;
      target.onload = () => (dt.needsUpdate = true);
      recolorImageSmart(
        ot.source.data as HTMLImageElement,
        (data, i) => {
          const alpha = data[i + 3] / 255;
          data[i] = Math.round(data[i] * alpha + red * (1 - alpha));
          data[i + 1] = Math.round(data[i + 1] * alpha + green * (1 - alpha));
          data[i + 2] = Math.round(data[i + 2] * alpha + blue * (1 - alpha));
          data[i + 3] = 255;
        },
        target,
      );
    }
  }
}
