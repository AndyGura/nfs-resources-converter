import { ClampToEdgeWrapping, Mesh, MeshBasicMaterial, Object3D, Texture, TextureLoader } from 'three';
import { setupNfs1Texture } from '../../common/obj-viewer/obj-viewer.component';
import { sleep } from '../../../../utils/sleep';
import { recolorImageSmart } from '../../../../utils/recolor-image';

export class Nfs2CarMeshController {
  // original/patched texture pairs
  textures: [Texture, Texture][] = [];

  tyreTextureUpdateTimer: number | undefined = undefined;
  tyreMaterial: MeshBasicMaterial | null = null;
  tyreTextures: Texture[] = [];

  private _color: number = 0x00ff00;
  get color(): number {
    return this._color;
  }

  set color(value: number) {
    if (value === this._color) return;
    this._color = value;
    this.recolorCar().then();
  }

  private _speed: 'idle' | 'slow' | 'fast' = 'idle';
  get speed(): 'idle' | 'slow' | 'fast' {
    return this._speed;
  }

  set speed(value: 'idle' | 'slow' | 'fast') {
    if (value === this._speed) return;
    this._speed = value;
    if (this.tyreTextureUpdateTimer) {
      clearInterval(this.tyreTextureUpdateTimer);
    }
    switch (value) {
      case 'idle':
        this.tyreMaterial!.map = this.tyreTextures[0];
        break;
      case 'slow':
        let flag = true;
        this.tyreTextureUpdateTimer = setInterval(() => {
          this.tyreMaterial!.map = this.tyreTextures[flag ? 1 : 2];
          this.tyreMaterial!.needsUpdate = true;
          flag = !flag;
        }, 16);
        break;
      case 'fast':
        this.tyreMaterial!.map = this.tyreTextures[3];
        break;
    }
    this.tyreMaterial!.needsUpdate = true;
  }

  get hasWheels(): boolean {
    return !!this.tyreMaterial;
  }

  constructor(private readonly mesh: Object3D) {
    let textures: Set<Texture> = new Set();
    mesh.traverse(o => {
      if (!(o instanceof Mesh)) {
        return;
      }
      if (['part_hp_12', 'part_hp_14', 'part_hp_16', 'part_hp_18'].includes(o.name)) {
        this.tyreMaterial = o.material;
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
    if (this.hasWheels) {
      this.tyreTextures = [this.tyreMaterial!.map!, null!, null!, null!];
      setTimeout(async () => {
        for (let i = 100; i > 0; i--) {
          if (!!this.tyreMaterial?.map?.source.data) break;
          await sleep(50);
        }
        const url = this.tyreMaterial?.map?.source.data.src || '';
        const loader = new TextureLoader();
        this.tyreTextures[1] = loader.load(url.replace('000', '100'));
        this.tyreTextures[2] = loader.load(url.replace('000', '200'));
        this.tyreTextures[3] = loader.load(url.replace('000', '300'));
        for (const t of this.tyreTextures) {
          setupNfs1Texture(t);
        }
        this.tyreMaterial!.transparent = true;
        this.tyreMaterial!.alphaTest = 0.5;
        this.tyreMaterial!.map!.wrapS = ClampToEdgeWrapping;
        this.tyreMaterial!.map!.wrapT = ClampToEdgeWrapping;
        this.tyreMaterial!.polygonOffset = true;
        this.tyreMaterial!.polygonOffsetFactor = -4;
      }, 0);
    }
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
