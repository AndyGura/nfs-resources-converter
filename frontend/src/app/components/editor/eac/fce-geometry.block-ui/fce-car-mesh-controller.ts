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

export type FceVersion = 3 | 4;

// FCE3: texture alpha of painted pixels: below this value it is primary color (car body), above it is secondary color
const FCE3_SECONDARY_COLOR_ALPHA_THRESHOLD = 160;

// FCE4: texture alpha of pixels, painted with primary, interior, secondary and driver hair color
const FCE4_COLOR_ALPHAS = [224, 164, 96, 32];

// FCE3: part indices of car.fce wheels, by LOD. Order: front left, front right, rear left, rear right
const FCE3_HIGH_POLY_WHEELS = [1, 2, 3, 4];
const FCE3_MEDIUM_POLY_WHEELS = [7, 6, 9, 8];

// FCE4: car.fce wheel part name: high/medium LOD, left/right, front/middle/rear
const FCE4_WHEEL_REGEX = /^(?:hp|mp)_\d+_[HM][LR]([FMR])W(?=__|_damaged$|$)/i;
// FCE4: front brakes steer together with wheels, but don't spin
const FCE4_BRAKE_REGEX = /^hp_\d+_O[LR]B(?=__|_damaged$|$)/i;

const WHEEL_SPIN_SPEED = { idle: 0, slow: 5, fast: 40 };

/**
 * Animates car.fce model in preview: steers and spins wheels, shows light dummies, recolors car. Expects meshes,
 * exported by Fce3GeometrySerializer/Fce4GeometrySerializer: "<lod>_<part index>_<part name>[__<texture>][_damaged]"
 */
export class FceCarMeshController {
  // every wheel can consist of a few meshes (one per texture, damaged copy)
  private wheels: { meshes: Mesh[]; isFront: boolean; spins: boolean }[] = [];
  private lights: Group | null = null;
  private spinAngle = 0;
  // original texture, its paint mask (alpha channel of car00.tga) and recolored texture, used by materials
  private paintTextures: { original: Texture; mask: HTMLImageElement; target: Texture }[] = [];

  // FCE3: primary, secondary. FCE4: primary, interior, secondary, driver hair
  private readonly colors: number[];

  getColor(index: number): number {
    return this.colors[index];
  }

  setColor(index: number, value: number) {
    this.colors[index] = value;
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
        // negative angle rolls wheels forward
        this.spinAngle -= WHEEL_SPIN_SPEED[this._speed] / 60;
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

  constructor(
    mesh: Object3D,
    private readonly version: FceVersion,
    dummies: FceDummy[],
    colors: number[],
  ) {
    this.colors = [...colors];
    this.setupPaintTextures(mesh);
    // wheel meshes by part index
    const parts: { [index: number]: { meshes: Mesh[]; isFront: boolean; spins: boolean } } = {};
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
      const isBody = version === 3 ? index === 0 : /^hp_\d+_HB(?=__|$)/i.test(o.name);
      if (isBody && !body) {
        body = o;
      }
      let wheel: { isFront: boolean; spins: boolean } | null = null;
      if (version === 3) {
        for (const wheelIndices of [FCE3_HIGH_POLY_WHEELS, FCE3_MEDIUM_POLY_WHEELS]) {
          if (wheelIndices.includes(index)) {
            wheel = { isFront: wheelIndices.indexOf(index) < 2, spins: true };
          }
        }
      } else {
        const wheelMatch = FCE4_WHEEL_REGEX.exec(o.name);
        if (wheelMatch) {
          wheel = { isFront: wheelMatch[1].toUpperCase() === 'F', spins: true };
        } else if (FCE4_BRAKE_REGEX.test(o.name)) {
          wheel = { isFront: true, spins: false };
        }
      }
      if (wheel) {
        (parts[index] = parts[index] || { meshes: [], ...wheel }).meshes.push(o);
      }
    });
    for (const wheel of Object.values(parts)) {
      // move pivot to the wheel center, so it rotates in place
      const box = new Box3();
      for (const m of wheel.meshes) {
        m.geometry.computeBoundingBox();
        box.union(m.geometry.boundingBox!);
      }
      const center = box.getCenter(new Vector3());
      for (const m of wheel.meshes) {
        m.geometry.translate(-center.x, -center.y, -center.z);
        m.position.copy(center);
        m.rotation.order = 'ZXY';
      }
      this.wheels.push(wheel);
    }
    const lightDummies = dummies.filter(d => FceCarMeshController.lightColor(version, d.name) !== null);
    if (body && lightDummies.length > 0) {
      this.lights = new Group();
      for (const dummy of lightDummies) {
        const light = new Mesh(
          new SphereGeometry(0.05, 8, 8),
          new MeshBasicMaterial({ color: FceCarMeshController.lightColor(version, dummy.name)! }),
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
    const colors = this.colors.map(c => [c >> 16, (c >> 8) & 0xff, c & 0xff]);
    for (const { original, mask, target } of this.paintTextures) {
      for (let i = 100; i > 0 && !((original.source.data as HTMLImageElement)?.complete && mask.complete); i--) {
        await sleep(50);
      }
      const image = original.source.data as HTMLImageElement;
      if (!image?.complete || !mask.complete) {
        continue;
      }
      const maskData = FceCarMeshController.readImageData(mask, image.width, image.height);
      recolorImageSmart(
        image,
        (data, i) => {
          const alpha = maskData ? maskData[i + 3] : 255;
          if (alpha === 0 || alpha === 255) {
            return;
          }
          // texture is a greyscale shading of the paint: mid-grey means exactly the paint color
          const [r, g, b] = colors[this.colorIndexByAlpha(alpha)];
          data[i] = Math.min(255, (data[i] * r) / 128);
          data[i + 1] = Math.min(255, (data[i + 1] * g) / 128);
          data[i + 2] = Math.min(255, (data[i + 2] * b) / 128);
        },
        target.source.data as HTMLImageElement,
      );
      target.needsUpdate = true;
    }
  }

  private colorIndexByAlpha(alpha: number): number {
    if (this.version === 3) {
      return alpha < FCE3_SECONDARY_COLOR_ALPHA_THRESHOLD ? 0 : 1;
    }
    let result = 0;
    FCE4_COLOR_ALPHAS.forEach((value, i) => {
      if (Math.abs(alpha - value) < Math.abs(alpha - FCE4_COLOR_ALPHAS[result])) {
        result = i;
      }
    });
    return result;
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

  /** Color of light dummy, null if dummy is not a light */
  private static lightColor(version: FceVersion, name: string): number | null {
    const kind = name.toUpperCase();
    if (version === 4) {
      // FCE4: special dummies start with ":" (license plate, smoke, water), lights have color as 2nd letter
      if (kind.startsWith(':')) {
        return null;
      }
      const color = { W: 0xffffcc, R: 0xff0000, B: 0x0000ff, O: 0xff8000, Y: 0xffff00 }[kind[1]];
      return color === undefined ? 0xff00ff : color;
    }
    // FCE3: light kind is the first letter: H - headlight, T - taillight, M - siren (with side as 3rd letter)
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
    for (const { meshes, isFront, spins } of this.wheels) {
      for (const m of meshes) {
        m.rotation.set(spins ? this.spinAngle : 0, 0, isFront ? this._steeringAngle : 0);
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
