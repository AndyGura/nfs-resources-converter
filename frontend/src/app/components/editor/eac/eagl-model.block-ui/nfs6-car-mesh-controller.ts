import { Group, Mesh, MeshBasicMaterial, Object3D, SphereGeometry, TextureLoader, Vector3 } from 'three';

export type Nfs6CarDummy = { name: string; position: [number, number, number] };

export type Nfs6CarSkin = { name: string; label: string; texture: string };

const WHEEL_SPIN_SPEED = { idle: 0, slow: 5, fast: 40 };

// geometry names of wheels ("ALPHA_OPAQUE_RUBBER_1Shape", "ALPHA_OPAQUE_RUBBER_LOD_WHEEL_2Shape") and brake calipers
// ("ALPHA_OPAQUE_BRAKE_3Shape"). Which wheel is which is not in the name, it is taken from the mesh position
const NFS6_WHEEL_REGEX = /^(?:hp|mp|lp)_\d+_\w*RUBBER/i;
const NFS6_BRAKE_REGEX = /^(?:hp|mp|lp)_\d+_\w*BRAKE/i;

// skeleton bones, drawn as lights
const NFS6_LIGHT_COLORS: [RegExp, number][] = [
  [/^LIGHT_TAIL/i, 0xff0000],
  [/^LIGHT_REVERSE/i, 0xffffff],
  [/^LIGHT_HEAD/i, 0xffffcc],
  [/^LIGHT_(?:COP|SIREN)/i, 0x0000ff],
];

/**
 * Animates NFS6 car model (car.o) in preview: steers and spins wheels (brake calipers steer only), switches skins,
 * shows light bones. Expects meshes, exported by EaglModelSerializer for a car: "<lod>_<index>_<geometry name>",
 * X right, Y forward, Z up. The paint is the texture "textures/skin.png", every skin has its own texture.
 * Depends only on three.js, so it can be reused outside the GUI
 */
export class Nfs6CarMeshController {
  private wheels: { meshes: Mesh[]; isFront: boolean; spins: boolean }[] = [];
  private lights: Group | null = null;
  private spinAngle = 0;
  // materials, which use the skin texture
  private skinMaterials: MeshBasicMaterial[] = [];
  private readonly textureLoader = new TextureLoader();
  private animationTimer: any = null;
  private baseUrl: string | null = null;

  private _skin: string | null = null;
  get skin(): string | null {
    return this._skin;
  }

  set skin(name: string | null) {
    const skin = this.skins.find(x => x.name === name);
    // folder of the exported model: skin textures are relative to it. Taken from the original skin texture URL
    if (!this.baseUrl) {
      const url: string | undefined = (this.skinMaterials[0]?.map?.source.data as HTMLImageElement)?.src;
      this.baseUrl = (url && /^(.*\/)textures\/skin\.png(\?.*)?$/.exec(url)?.[1]) || null;
    }
    const baseUrl = this.baseUrl;
    if (!skin || !baseUrl) {
      return;
    }
    this._skin = name;
    this.textureLoader.load(baseUrl + skin.texture, texture => {
      for (const material of this.skinMaterials) {
        const original = material.map!;
        texture.flipY = original.flipY;
        texture.wrapS = original.wrapS;
        texture.wrapT = original.wrapT;
        texture.colorSpace = original.colorSpace;
        texture.anisotropy = original.anisotropy;
        texture.magFilter = original.magFilter;
        texture.minFilter = original.minFilter;
        texture.needsUpdate = true;
        material.map = texture;
        material.needsUpdate = true;
      }
    });
  }

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
    dummies: Nfs6CarDummy[],
    readonly skins: Nfs6CarSkin[],
  ) {
    this.setupWheels(mesh);
    this.setupSkinMaterials(mesh);
    const lightDummies = dummies.filter(d => Nfs6CarMeshController.lightColor(d.name) !== null);
    if (lightDummies.length > 0) {
      this.lights = new Group();
      this.lights.visible = false;
      for (const dummy of lightDummies) {
        const light = new Mesh(
          new SphereGeometry(0.05, 8, 8),
          new MeshBasicMaterial({ color: Nfs6CarMeshController.lightColor(dummy.name)! }),
        );
        light.name = dummy.name;
        light.position.set(...dummy.position);
        this.lights.add(light);
      }
      mesh.add(this.lights);
    }
    if (this.skins.length > 0 && this.skinMaterials.length > 0) {
      this._skin = this.skins[0].name;
    }
  }

  private setupWheels(mesh: Object3D) {
    const wheelMeshes: Mesh[] = [];
    const brakeMeshes: Mesh[] = [];
    mesh.traverse(o => {
      if (o instanceof Mesh) {
        if (NFS6_WHEEL_REGEX.test(o.name)) {
          wheelMeshes.push(o);
        } else if (NFS6_BRAKE_REGEX.test(o.name)) {
          brakeMeshes.push(o);
        }
      }
    });
    const wheelCenters: Vector3[] = [];
    const centerOf = (m: Mesh) => {
      m.geometry.computeBoundingBox();
      return m.geometry.boundingBox!.getCenter(new Vector3());
    };
    const setPivot = (m: Mesh, pivot: Vector3) => {
      m.geometry.translate(-pivot.x, -pivot.y, -pivot.z);
      m.position.copy(pivot);
      m.rotation.order = 'ZXY';
    };
    for (const m of wheelMeshes) {
      // move pivot to the wheel center, so it rotates in place
      const center = centerOf(m);
      wheelCenters.push(center);
      setPivot(m, center);
      this.wheels.push({ meshes: [m], isFront: center.y > 0, spins: true });
    }
    for (const m of brakeMeshes) {
      // brake caliper turns around the center of its wheel
      const center = centerOf(m);
      const pivot = wheelCenters.reduce<Vector3 | null>(
        (best, c) => (!best || c.distanceTo(center) < best.distanceTo(center) ? c : best),
        null,
      );
      setPivot(m, pivot ? new Vector3(center.x, pivot.y, pivot.z) : center);
      this.wheels.push({ meshes: [m], isFront: center.y > 0, spins: false });
    }
  }

  /** Materials, named after the texture "skin" (the paint) */
  private setupSkinMaterials(mesh: Object3D) {
    mesh.traverse(o => {
      if (!(o instanceof Mesh)) {
        return;
      }
      const materials = o.material instanceof Array ? o.material : [o.material];
      for (const material of materials) {
        if (material.name === 'skin' && (material as MeshBasicMaterial).map && !this.skinMaterials.includes(material)) {
          this.skinMaterials.push(material as MeshBasicMaterial);
        }
      }
    });
  }

  /** Color of light bone, null if bone is not a light */
  private static lightColor(name: string): number | null {
    return NFS6_LIGHT_COLORS.find(([regex]) => regex.test(name))?.[1] ?? null;
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
