import { ClampToEdgeWrapping, Mesh, MeshBasicMaterial, Object3D, Texture, TextureLoader } from 'three';
import { setupNfs1Texture } from '../../common/obj-viewer/obj-viewer.component';
import { sleep } from '../../../../utils/sleep';
import { replaceColor } from '../../../../utils/recolor-image';

export class Nfs1CarMeshController {
  // original texture
  originalTexWithTailLights: Texture | null = null;
  tyreMaterial: MeshBasicMaterial | null = null;

  // runtime texture
  texWithTailLightsImg: HTMLImageElement | null = null;
  texWithTailLights: Texture | null = null;
  tailLightColors: [number, number] = [0, 0];
  tyreTextures: Texture[] = [];
  tyreTextureUpdateTimer: number | undefined = undefined;

  private _tailLightsOn: boolean = false;
  get tailLightsOn(): boolean {
    return this._tailLightsOn;
  }

  set tailLightsOn(value: boolean) {
    if (value === this._tailLightsOn) return;
    this._tailLightsOn = value;
    this.recolorTailLights(this.tailLightColors[value ? 1 : 0]);
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
        }, 16) as any;
        break;
      case 'fast':
        this.tyreMaterial!.map = this.tyreTextures[3];
        break;
    }
    this.tyreMaterial!.needsUpdate = true;
  }

  constructor(
    private readonly mesh: Object3D,
    private readonly tailLightsTexColor: number,
    private readonly assetsPath: string,
  ) {
    const wheelObjects: Mesh[] = [];
    const headlightsObjects: Mesh[] = [];
    mesh.traverse(o => {
      if (!(o instanceof Mesh)) {
        return;
      }
      if (o.name.startsWith('lbl__lt_') || o.name.startsWith('lbl__rt_')) {
        wheelObjects.push(o);
      }
      if (['lbl__bkll', 'lbl__bklr', 'lite'].includes(o.name)) {
        headlightsObjects.push(o);
        this.originalTexWithTailLights = o.material.map;
      }
    });
    if (!this.originalTexWithTailLights) {
      throw new Error('Not a driveable NFS1 car');
    }

    // TODO colors seem to be different for different cars, but I don't know how it is defined in the game
    this.tailLightColors = assetsPath.includes('TRAFFC.CFM') ? [0x911c0f, 0xff0000] : [0x310502, 0xf81414];
    this.texWithTailLightsImg = document.createElement('img');
    this.texWithTailLights = new Texture(this.texWithTailLightsImg);
    this.texWithTailLights.flipY = this.originalTexWithTailLights.flipY;
    setupNfs1Texture(this.texWithTailLights);
    this.recolorTailLights(this.tailLightColors[0]).then();
    for (const o of headlightsObjects) {
      (o.material as MeshBasicMaterial).map = this.texWithTailLights;
    }

    const loader = new TextureLoader();
    this.tyreTextures = [1, 2, 3, 4].map(i => loader.load(`${assetsPath}/tyr${i}.png`));
    for (const t of this.tyreTextures) {
      setupNfs1Texture(t);
    }
    this.tyreMaterial = new MeshBasicMaterial({ map: this.tyreTextures[0] });
    this.tyreMaterial.transparent = true;
    this.tyreMaterial.alphaTest = 0.5;
    this.tyreMaterial.map!.wrapS = ClampToEdgeWrapping;
    this.tyreMaterial.map!.wrapT = ClampToEdgeWrapping;
    this.tyreMaterial.polygonOffset = true;
    this.tyreMaterial.polygonOffsetFactor = -4;
    for (const o of wheelObjects) {
      o.material = this.tyreMaterial;
    }
  }

  async recolorTailLights(newColor: number) {
    if (!this.originalTexWithTailLights || !this.texWithTailLights || !this.texWithTailLightsImg) return;
    for (let i = 100; i > 0; i--) {
      if (!!this.originalTexWithTailLights.source.data) break;
      await sleep(50);
    }
    replaceColor(
      this.originalTexWithTailLights.source.data,
      this.tailLightsTexColor,
      newColor,
      this.texWithTailLightsImg,
    );
    this.texWithTailLights.needsUpdate = true;
  }

  public dispose() {
    if (this.texWithTailLightsImg) {
      this.texWithTailLightsImg.remove();
      this.texWithTailLightsImg = null;
    }
    if (this.texWithTailLights) {
      this.texWithTailLights.dispose();
      this.texWithTailLights = null;
    }
    if (this.tyreTextureUpdateTimer) {
      clearInterval(this.tyreTextureUpdateTimer);
    }
    if (this.tyreMaterial) {
      this.tyreMaterial.dispose();
      this.tyreMaterial = null;
    }
  }
}
