import { Box3, Group, Mesh, MeshBasicMaterial, Object3D, SphereGeometry, Texture, Vector3 } from 'three';
import { setupNfs1Texture } from '../../common/obj-viewer/obj-viewer.component';
import { sleep } from '../../../../utils/sleep';
import { recolorImageSmart } from '../../../../utils/recolor-image';

export type FceDummy = { name: string; position: [number, number, number] };

export type FceColor = { hue: number; saturation: number; brightness: number; transparency: number };

/** FCE color (HSB, every component is 0..255) to 0xRRGGBB */
export const fceColorToRgb = (color: FceColor): number => {
  const h = (color.hue / 255) * 6;
  const s = color.saturation / 255;
  const v = color.brightness / 255;
  const f = (n: number) => {
    const k = (n + h) % 6;
    return Math.round(255 * (v - v * s * Math.max(0, Math.min(k, 4 - k, 1))));
  };
  return (f(5) << 16) | (f(3) << 8) | f(1);
};

// texture alpha of painted pixels: below this value it is primary color (car body), above it is secondary color
const SECONDARY_COLOR_ALPHA_THRESHOLD = 160;

// part indices of car.fce wheels, by LOD. Order: front left, front right, rear left, rear right
const HIGH_POLY_WHEELS = [1, 2, 3, 4];
const MEDIUM_POLY_WHEELS = [7, 6, 9, 8];

const WHEEL_SPIN_SPEED = { idle: 0, slow: 5, fast: 40 };

/**
 * Animates car.fce model in preview: steers and spins wheels, shows light dummies. Expects meshes, exported by
 * Fce3GeometrySerializer: "<lod>_<part index>_..."
 */
export class Fce3CarMeshController {
  // every wheel can consist of a few meshes (one per texture)
  private wheels: { meshes: Mesh[]; isFront: boolean }[] = [];
  private lights: Group | null = null;
  private spinAngle = 0;
  // original texture, its paint mask (alpha channel of car00.tga) and recolored texture, used by materials
  private paintTextures: { original: Texture; mask: HTMLImageElement; target: Texture }[] = [];

  private _primaryColor: number;
  get primaryColor(): number {
    return this._primaryColor;
  }

  set primaryColor(value: number) {
    this._primaryColor = value;
    this.recolorCar().then();
  }

  private _secondaryColor: number;
  get secondaryColor(): number {
    return this._secondaryColor;
  }

  set secondaryColor(value: number) {
    this._secondaryColor = value;
    this.recolorCar().then();
  }

  get isPaintable(): boolean {
    return this.paintTextures.length > 0;
  }
  private animationTimer: any = null;

  private _speed: 'idle' | 'slow' | 'fast' = 'idle';
  get speed(): 'idle' | 'slow' | 'fast' {
    return this._speed;
  }

  set speed(value: 'idle' | 'slow' | 'fast') {
    this._speed = value;
    if (this.animationTimer) {
      clearInterval(this.animationTimer);
      this.animationTimer = null;
    }
    if (value !== 'idle') {
      this.animationTimer = setInterval(() => {
        this.spinAngle += WHEEL_SPIN_SPEED[this._speed] / 60;
        this.updateWheels();
      }, 1000 / 60);
    }
  }

  private _steeringAngle: number = 0;
  get steeringAngle(): number {
    return this._steeringAngle;
  }

  set steeringAngle(value: number) {
    this._steeringAngle = value;
    this.updateWheels();
  }

  get showLights(): boolean {
    return !!this.lights?.visible;
  }

  set showLights(value: boolean) {
    if (this.lights) {
      this.lights.visible = value;
    }
  }

  get hasWheels(): boolean {
    return this.wheels.length > 0;
  }

  get hasLights(): boolean {
    return !!this.lights;
  }

  constructor(mesh: Object3D, dummies: FceDummy[], primaryColor: number, secondaryColor: number) {
    this._primaryColor = primaryColor;
    this._secondaryColor = secondaryColor;
    this.setupPaintTextures(mesh);
    const parts: { [index: number]: Mesh[] } = {};
    let body: Mesh | null = null;
    mesh.traverse(o => {
      if (!(o instanceof Mesh)) {
        return;
      }
      const match = /^(hp|mp)_(\d+)/.exec(o.name);
      if (!match) {
        return;
      }
      const index = +match[2];
      if (index === 0 && !body) {
        body = o;
      }
      if ([...HIGH_POLY_WHEELS, ...MEDIUM_POLY_WHEELS].includes(index)) {
        (parts[index] = parts[index] || []).push(o);
      }
    });
    for (const wheelIndices of [HIGH_POLY_WHEELS, MEDIUM_POLY_WHEELS]) {
      wheelIndices.forEach((partIndex, i) => {
        const meshes = parts[partIndex];
        if (!meshes) {
          return;
        }
        // move pivot to the wheel center, so it rotates in place
        const box = new Box3();
        for (const m of meshes) {
          m.geometry.computeBoundingBox();
          box.union(m.geometry.boundingBox!);
        }
        const center = box.getCenter(new Vector3());
        for (const m of meshes) {
          m.geometry.translate(-center.x, -center.y, -center.z);
          m.position.copy(center);
          m.rotation.order = 'ZXY';
        }
        this.wheels.push({ meshes, isFront: i < 2 });
      });
    }
    if (body && dummies.length > 0) {
      this.lights = new Group();
      for (const dummy of dummies) {
        const light = new Mesh(
          new SphereGeometry(0.05, 8, 8),
          new MeshBasicMaterial({ color: Fce3CarMeshController.lightColor(dummy.name) }),
        );
        light.name = dummy.name;
        light.position.set(...dummy.position);
        this.lights.add(light);
      }
      (body as Mesh).add(this.lights);
    }
    this.recolorCar().then();
  }

  /** Replaces textures of materials with recolorable copies, if texture has a paint mask (<texture>_paint_mask.png) */
  private setupPaintTextures(mesh: Object3D) {
    mesh.traverse(o => {
      if (!(o instanceof Mesh)) {
        return;
      }
      const materials = o.material instanceof Array ? o.material : [o.material];
      for (const material of materials) {
        const original: Texture | null = (material as MeshBasicMaterial).map;
        if (!original) {
          continue;
        }
        let paintTexture = this.paintTextures.find(x => x.original === original || x.target === original);
        if (!paintTexture) {
          const url: string | undefined = (original.source.data as HTMLImageElement)?.src;
          if (!url || !/\.png(\?.*)?$/.test(url)) {
            continue;
          }
          const mask = document.createElement('img');
          mask.src = url.replace(/\.png(\?.*)?$/, '_paint_mask.png$1');
          const target = new Texture(document.createElement('img'));
          target.flipY = original.flipY;
          target.wrapS = original.wrapS;
          target.wrapT = original.wrapT;
          setupNfs1Texture(target);
          paintTexture = { original, mask, target };
          this.paintTextures.push(paintTexture);
        }
        (material as MeshBasicMaterial).map = paintTexture.target;
      }
    });
  }

  async recolorCar() {
    const colors = [this._primaryColor, this._secondaryColor].map(c => [c >> 16, (c >> 8) & 0xff, c & 0xff]);
    for (const { original, mask, target } of this.paintTextures) {
      for (let i = 100; i > 0 && !((original.source.data as HTMLImageElement)?.complete && mask.complete); i--) {
        await sleep(50);
      }
      const image = original.source.data as HTMLImageElement;
      if (!image?.complete || !mask.complete) {
        continue;
      }
      const maskData = Fce3CarMeshController.readImageData(mask, image.width, image.height);
      recolorImageSmart(
        image,
        (data, i) => {
          const alpha = maskData ? maskData[i + 3] : 255;
          if (alpha === 0 || alpha === 255) {
            return;
          }
          // texture is a greyscale shading of the paint: mid-grey means exactly the paint color
          const [r, g, b] = colors[alpha < SECONDARY_COLOR_ALPHA_THRESHOLD ? 0 : 1];
          data[i] = Math.min(255, (data[i] * r) / 128);
          data[i + 1] = Math.min(255, (data[i + 1] * g) / 128);
          data[i + 2] = Math.min(255, (data[i + 2] * b) / 128);
        },
        target.source.data as HTMLImageElement,
      );
      target.needsUpdate = true;
    }
  }

  private static readImageData(img: HTMLImageElement, width: number, height: number): Uint8ClampedArray | null {
    if (!img.naturalWidth) {
      // no paint mask: texture is not recolored
      return null;
    }
    const c = document.createElement('canvas');
    c.width = width;
    c.height = height;
    const ctx = c.getContext('2d', { willReadFrequently: true })!;
    ctx.drawImage(img, 0, 0, width, height);
    const data = ctx.getImageData(0, 0, width, height).data;
    c.remove();
    return data;
  }

  // light kind is the first letter of dummy name: H - headlight, T - taillight, M - siren (with side as 3rd letter)
  private static lightColor(name: string): number {
    const kind = name.toUpperCase();
    if (kind.startsWith('H')) {
      return 0xffffcc;
    } else if (kind.startsWith('T')) {
      return 0xff0000;
    } else if (kind.startsWith('M')) {
      return kind[2] === 'L' ? 0xff0000 : 0x0000ff;
    }
    return 0xff00ff;
  }

  private updateWheels() {
    for (const { meshes, isFront } of this.wheels) {
      for (const m of meshes) {
        m.rotation.set(this.spinAngle, 0, isFront ? this._steeringAngle : 0);
      }
    }
  }

  dispose() {
    if (this.animationTimer) {
      clearInterval(this.animationTimer);
      this.animationTimer = null;
    }
  }
}
