import { ClampToEdgeWrapping, Mesh, MeshBasicMaterial, Object3D, Texture, TextureLoader } from 'three';
import { setupNfs1Texture } from '../../common/obj-viewer/obj-viewer.component';
import { sleep } from '../../../../utils/sleep';
import { replaceColor } from '../../../../utils/recolor-image';
import { Pnt3, Point3 } from '@gg-web-engine/core';

export class TnfsCarMeshController {
  // original texture
  originalTexWithTailLights: Texture | null = null;
  tyreMaterial: MeshBasicMaterial | null = null;

  // runtime texture
  texWithTailLightsImg: HTMLImageElement | null = null;
  texWithTailLights: Texture | null = null;
  tailLightColors: [number, number] = [0, 0];
  tyreTextures: Texture[] = [];
  tyreTextureUpdateTimer: number | undefined = undefined;

  // order: front right, front left, rear right, rear left
  public wheels: Mesh[] = [];
  public wheelIdlePositions: Point3[] = [];
  // order: right, left
  public frontWheels: Mesh[] = [];

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

  private _steeringAngle: number = 0;
  get steeringAngle(): number {
    return this._steeringAngle;
  }

  set steeringAngle(value: number) {
    if (value === this._steeringAngle) return;
    this._steeringAngle = value;
    for (const wheel of this.frontWheels) {
      wheel.rotation.set(0, 0, value);
    }
  }

  constructor(
    private readonly mesh: Object3D,
    private readonly tailLightsTexColor: number,
    private readonly assetsPath: string,
  ) {
    const headlightsObjects: Mesh[] = [];
    this.wheels = [null!, null!, null!, null!];
    this.frontWheels = [null!, null!];
    mesh.traverse(o => {
      if (!(o instanceof Mesh)) {
        return;
      }
      let wheelIndex = -1;
      if (o.name.startsWith('lbl__rt_frnt')) {
        wheelIndex = 0;
      } else if (o.name.startsWith('lbl__lt_frnt')) {
        wheelIndex = 1;
      } else if (o.name.startsWith('lbl__rt_rear')) {
        wheelIndex = 2;
      } else if (o.name.startsWith('lbl__lt_rear')) {
        wheelIndex = 3;
      }
      if (wheelIndex > -1) {
        this.wheels[wheelIndex] = o;
        if (wheelIndex < 2) {
          this.frontWheels[wheelIndex] = o;
        }
        if (!o.geometry.boundingBox) {
          o.geometry.computeBoundingBox();
        }
        const wheelPos = Pnt3.avg(o.geometry.boundingBox!.min, o.geometry.boundingBox!.max);
        o.geometry!.translate(...Pnt3.spr(Pnt3.neg(wheelPos)));
        o.position.set(...Pnt3.spr(wheelPos));
        this.wheelIdlePositions[wheelIndex] = wheelPos;
      }
      if (o.name.includes('rsid') || o.name.includes('lite')) {
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
    for (const o of this.wheels) {
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
