import { Mesh, MeshBasicMaterial, Object3D, Texture } from 'three';
import { setupNfs1Texture } from '../../common/obj-viewer/obj-viewer.component';
import { sleep } from '../../../../utils/sleep';
import { recolorImageSmart } from '../../../../utils/recolor-image';

export class Nfs2CarMeshController {
  // original/patched texture pairs
  textures: [Texture, Texture][] = [];

  private _color: number = 0x00ff00;
  get color(): number {
    return this._color;
  }

  set color(value: number) {
    if (value === this._color) return;
    this._color = value;
    this.recolorCar().then();
  }

  constructor(private readonly mesh: Object3D) {
    let textures: Set<Texture> = new Set();
    mesh.traverse(o => {
      if (!(o instanceof Mesh)) {
        return;
      }
      const t = (o.material as MeshBasicMaterial).map;
      if (t) {
        textures.add(t);
      }
    });
    // create textures
    this.textures = Array.from(textures).map(t => {
      const newTex = new Texture(document.createElement('img'));
      setupNfs1Texture(newTex);
      return [t, newTex];
    });
    // replace textures
    mesh.traverse(o => {
      if (!(o instanceof Mesh)) {
        return;
      }
      const t = (o.material as MeshBasicMaterial).map;
      if (t) {
        const patch = this.textures.find(([tx, _]) => tx === t);
        if (patch) {
          (o.material as MeshBasicMaterial).map = patch[1];
        }
      }
    });
    this.color = 0x00ff00;
    this.recolorCar().then();
  }

  async recolorCar() {
    const [newRed, newGreen, newBlue] = [this.color >> 16, (this.color >> 8) & 0xff, this.color & 0xff];
    for (const [ot, dt] of this.textures) {
      for (let i = 100; i > 0; i--) {
        if (!!ot.source.data) break;
        await sleep(50);
      }
      recolorImageSmart(
        ot.source.data,
        (data, i) => {
          if (data[i] == 0 && data[i + 2] == 0) {
            const greenComponent = data[i + 1];
            data[i] = Math.round((newRed * greenComponent) / 255);
            data[i + 1] = Math.round((newGreen * greenComponent) / 255);
            data[i + 2] = Math.round((newBlue * greenComponent) / 255);
          }
        },
        dt.source.data,
      );
      dt.needsUpdate = true;
    }
  }
}
