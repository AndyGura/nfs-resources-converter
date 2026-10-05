import { Box3, Group, Mesh, MeshBasicMaterial, Object3D, SphereGeometry, Vector3 } from 'three';

export type FceDummy = { name: string; position: [number, number, number] };

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

  constructor(mesh: Object3D, dummies: FceDummy[]) {
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
