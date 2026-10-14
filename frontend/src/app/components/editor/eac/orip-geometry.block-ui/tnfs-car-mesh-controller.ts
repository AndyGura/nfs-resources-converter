import {
  Camera,
  ClampToEdgeWrapping,
  Material,
  Mesh,
  MeshBasicMaterial,
  Object3D,
  Texture,
  TextureLoader,
  Vector3,
} from 'three';
import { setupNfs1Texture } from '../../common/obj-viewer/obj-viewer.component';
import { Pnt3, Point3 } from '@gg-web-engine/core';
import { sleep } from '../../../../utils/sleep';
import { replaceColor } from '../../../../utils/recolor-image';

// tnfs_car_data.tire_skid_front/rear bits, set by the player's physics (tnfs_car_tire_force): wheels locked (brakes,
// handbrake) or sliding sideways past the cutoff angle; wheelspin
export const TYRE_SKID_LOCKED = 1;
export const TYRE_SKID_SPIN = 2;

// gfx_car_tyre_textures: one drawn frame per 30 Hz tick; speeds in physics m/s (16.16 0x1999, 0xa0000, 0x1e0000)
const TYRE_FRAME_MS = 1000 / 30;
const MAX_TYRE_FRAMES_PER_UPDATE = 4;
const TYRE_STILL_SPEED = 0x1999 / 0x10000;
const TYRE_FLICKER_SPEED = 10;
const TYRE_FAST_SPEED = 30;
// position change in a frame under which the front tyres stand (0x1999, |dx| + |dy|)
const TYRE_STILL_MOVE = 0x1999 / 0x10000;

/*
 * How the original draws a car (DOS gfx_draw_car_model 0x74766, gfx_ori_sort_polys 0xa1a00; PSX and SE the same): the
 * model's polygons are in partitions, drawn one after the other, each depth-sorted on its own: `inside` (circ, the
 * inner tyre faces; shad, the tyre bottoms seen from the front and back), then `surface` (the body), then `outside`
 * (the four wheel quads). So the wheels are always painted over their own body when they face the camera (they are
 * single-sided: the far ones are culled), and the inside parts always under it. The converter writes the partition
 * of each mesh into its node extras (`userData.partition`); models converted before have none: see partitionOf.
 */
// The original has no depth test: it paints the wheels over their own body whatever the distance. In a z-buffer they
// are moved toward the camera along the view ray instead (the screen position stays, the depth shrinks), only as far as
// the own body can be in front of them: a body point between a wheel and the camera is at most `gap` farther out than
// the wheel (the body's widest point minus the wheel's innermost one, per axle; a steered front wheel's inner edge
// moves in), so along the ray at most gap / sin(angle between the ray and the car's side). Most cars: gap 0-5 cm, the
// Diablo's front 13 cm, the Warrior's rear 24 cm, plus up to ~22 cm on a fully steered front wheel. Up to this grazing
// angle (5 degrees, where the wheel is a sliver), beyond it the bias stays. Other cars and objects closer than the bias
// in front of a wheel get it over them
const WHEEL_BIAS_MIN_SIN = Math.sin((5 * Math.PI) / 180);
// against depth precision
const WHEEL_BIAS_MARGIN = 0.02;
// how far a steered front wheel's inner edge can move in when the model has no steering morphs (turned by rotation)
const WHEEL_STEER_ROTATION_GAP = 0.2;
// the inside parts lose against the body where they meet it
const INSIDE_POLYGON_OFFSET = 2;

// gfx_car_steer_wheel_morphs (DOS 0x73f7f, SE 0x458818): the front wheels (and their inner circ quads) are morphed
// toward left_turn / right_turn with weight -steer_angle / 0x200000 (both morphs turn their wheel left at a positive
// weight; 0x200000 = 45 degrees of steer_angle), each only while its side faces the camera: the direction to the camera
// at least 0xa0000 (14.06 degrees) away from the car's long axis. Not a rotation: the morph of weight 1 turns the wheel
// about 30 degrees. The game morphs the player's car only, here every car is
const STEER_MORPH_WEIGHT_PER_RAD = 1 / (Math.PI / 4);
const STEER_MORPH_MIN_SIDE = Math.sin((0xa0000 / 0x1000000) * 2 * Math.PI);

type CarPartition = 'inside' | 'surface' | 'outside';

/** A mesh's partition (see above), by the converter's extras, else by name for the models converted before */
function partitionOf(mesh: Mesh): CarPartition {
  const partition = mesh.userData?.['partition'];
  if (partition === 'inside' || partition === 'surface' || partition === 'outside') {
    return partition;
  }
  if (mesh.name.startsWith('lbl__lt_') || mesh.name.startsWith('lbl__rt_')) {
    return 'outside';
  }
  return ['circ', 'shad'].includes(mesh.name) ? 'inside' : 'surface';
}

/** Moves a wheel's vertices toward the camera along their view ray, for a body up to `gap` outside it (see above) */
function biasTowardCamera(material: Material, gap: { value: number }) {
  material.onBeforeCompile = shader => {
    shader.uniforms['wheelBiasGap'] = gap;
    shader.vertexShader = shader.vertexShader.replace(
      '#include <common>',
      '#include <common>\nuniform float wheelBiasGap;',
    );
    shader.vertexShader = shader.vertexShader.replace(
      '#include <project_vertex>',
      `#include <project_vertex>
      {
        float viewDistance = length(mvPosition.xyz);
        vec3 side = normalize((modelViewMatrix * vec4(1.0, 0.0, 0.0, 0.0)).xyz);
        float sinToSide = max(abs(dot(mvPosition.xyz, side)) / max(viewDistance, 1e-6), ${WHEEL_BIAS_MIN_SIN.toFixed(4)});
        float bias = wheelBiasGap / sinToSide + ${WHEEL_BIAS_MARGIN.toFixed(3)};
        float biased = max(viewDistance - bias, min(viewDistance, 0.2));
        gl_Position = projectionMatrix * vec4(mvPosition.xyz * (biased / max(viewDistance, 1e-6)), 1.0);
      }`,
    );
  };
  material.customProgramCacheKey = () => 'tnfs-wheel-bias';
}

export class TnfsCarMeshController {
  // original texture
  originalTexWithTailLights: Texture | null = null;
  frontTyreMaterial: MeshBasicMaterial | null = null;
  rearTyreMaterial: MeshBasicMaterial | null = null;

  // runtime texture
  texWithTailLightsImg: HTMLImageElement | null = null;
  texWithTailLights: Texture | null = null;
  tailLightColors: [number, number] = [0, 0];
  // tyr1..tyr4 on both axles: the game puts them on frntires and rertires, the Warrior's rear rty* are never shown
  tyreTextures: Texture[] = [];
  private frontTyreIndex = 0;
  private rearTyreIndex = 0;
  // the original's frame phases (start values as there) and the position at the previous frame, see updateTyres
  private tyreFrameTime = 0;
  private tyrePhase = 1;
  private tyrePhaseSlow = 1;
  private tyrePrevPosition: Point3 | null = null;
  // the Diablo's front tyres turn whether the car moves or not, see updateTyres
  private readonly frontTyresIgnoreMotion: boolean;

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

  /**
   * Tyre textures as the original animates the player's car (DOS gfx_car_tyre_textures 0x73c26, PSX 0x8004f370, SE
   * 0x458614), once per drawn frame. The game draws at most one frame per 30 Hz physics tick: here a frame is 1/30 s of
   * game time, whatever the render rate. Index 0..3 = tyr1..tyr4, on both axles.
   * - the speed (|speed_local_lon|, physics m/s): over 30 m/s tyr4, under 0.1 m/s tyr1, between them tyr3/tyr2 flipping
   *   every frame from 10 m/s, every second frame below;
   * - per axle the tyre skid bits override it: TYRE_SKID_LOCKED tyr1, else TYRE_SKID_SPIN tyr4;
   * - the front tyres also stand (tyr1) while the car moved less than 0.1 m in the frame, except on the Diablo (car model
   *   id 1; id 10 too, a car not identified yet). The original measures that on x and the height (a bug: driving along
   *   z it stops the front tyres), here on the ground plane.
   * The original keeps the frame phases and the previous position in globals, for the player's car only: each car has
   * its own here, every car is animated (AI racers keep tyr4 in the original).
   */
  updateTyres(deltaMs: number, speed: number, skidFront: number, skidRear: number, position: Point3): void {
    this.tyreFrameTime += deltaMs;
    let frames = Math.floor(this.tyreFrameTime / TYRE_FRAME_MS);
    if (frames < 1) {
      return;
    }
    this.tyreFrameTime -= frames * TYRE_FRAME_MS;
    if (frames > MAX_TYRE_FRAMES_PER_UPDATE) {
      // a long stall (tab in background): don't play the missed frames
      frames = MAX_TYRE_FRAMES_PER_UPDATE;
      this.tyreFrameTime = 0;
    }
    const s = Math.abs(speed);
    let index: number;
    if (s > TYRE_FAST_SPEED) {
      index = 3;
    } else if (s < TYRE_STILL_SPEED) {
      index = 0;
    } else {
      for (let i = 0; i < frames; i++) {
        this.tyrePhase = 1 - this.tyrePhase;
        if (this.tyrePhase) {
          this.tyrePhaseSlow = 1 - this.tyrePhaseSlow;
        }
      }
      index = (s >= TYRE_FLICKER_SPEED ? this.tyrePhase : this.tyrePhaseSlow) + 1;
    }
    const prev = this.tyrePrevPosition;
    this.tyrePrevPosition = { ...position };
    const moved = prev ? (Math.abs(position.x - prev.x) + Math.abs(position.y - prev.y)) / frames : 0;
    const axle = (skid: number, i: number) => (skid & TYRE_SKID_LOCKED ? 0 : skid & TYRE_SKID_SPIN ? 3 : i);
    const rear = axle(skidRear, index);
    const front =
      skidFront & TYRE_SKID_LOCKED || (!this.frontTyresIgnoreMotion && moved < TYRE_STILL_MOVE)
        ? 0
        : axle(skidFront, index);
    this.setTyreIndices(front, rear);
  }

  /** Front and rear tyre texture index, see updateTyres */
  setTyreIndices(front: number, rear: number, force = false): void {
    if (force || front !== this.frontTyreIndex) {
      this.frontTyreIndex = front;
      this.frontTyreMaterial!.map = this.tyreTextures[front];
      this.frontTyreMaterial!.needsUpdate = true;
    }
    if (force || rear !== this.rearTyreIndex) {
      this.rearTyreIndex = rear;
      this.rearTyreMaterial!.map = this.tyreTextures[rear];
      this.rearTyreMaterial!.needsUpdate = true;
    }
  }

  // meshes with the steering morphs (front wheels, circ), see STEER_MORPH_WEIGHT_PER_RAD; none in models converted
  // before the morphs were exported: then the front wheels are turned
  private readonly steerMorphMeshes: Mesh[] = [];
  private steerMorphWeight = 0;
  // the wheels' depth bias gaps (see WHEEL_BIAS_MIN_SIN): the front one grows with the steering
  private readonly frontWheelGap = { value: 0 };
  private readonly rearWheelGap = { value: 0 };
  private frontWheelStraightGap = 0;
  // how far the steering morph of weight 1 moves a vertex sideways at most
  private steerMorphDx = 0;
  // the sign of x on the car's left side (the side of lt_frnt)
  private leftSideSign = 1;

  private _steeringAngle: number = 0;
  get steeringAngle(): number {
    return this._steeringAngle;
  }

  /** Steering angle of the front wheels in radians, positive to the left */
  set steeringAngle(value: number) {
    if (value === this._steeringAngle) return;
    this._steeringAngle = value;
    if (this.steerMorphMeshes.length > 0) {
      this.steerMorphWeight = value * STEER_MORPH_WEIGHT_PER_RAD;
      this.frontWheelGap.value = this.frontWheelStraightGap + Math.abs(this.steerMorphWeight) * this.steerMorphDx;
      return;
    }
    for (const wheel of this.frontWheels) {
      wheel.rotation.set(0, 0, value);
    }
  }

  /** Before each render of a morphed mesh: the steering morph of the side that faces this camera, see above */
  private applySteerMorphs(mesh: Mesh, camera: Camera) {
    const dictionary = mesh.morphTargetDictionary;
    const influences = mesh.morphTargetInfluences;
    if (!dictionary || !influences) {
      return;
    }
    const toCamera = this.mesh.worldToLocal(camera.getWorldPosition(this.cameraPosition));
    const horizontal = Math.hypot(toCamera.x, toCamera.y);
    const sideVisible = horizontal > 0 && Math.abs(toCamera.x) >= STEER_MORPH_MIN_SIDE * horizontal;
    const leftVisible = sideVisible && Math.sign(toCamera.x) === this.leftSideSign;
    const rightVisible = sideVisible && !leftVisible;
    if (dictionary['left_turn'] !== undefined) {
      influences[dictionary['left_turn']] = leftVisible ? this.steerMorphWeight : 0;
    }
    if (dictionary['right_turn'] !== undefined) {
      influences[dictionary['right_turn']] = rightVisible ? this.steerMorphWeight : 0;
    }
  }

  private readonly cameraPosition = new Vector3();

  constructor(
    private readonly mesh: Object3D,
    private readonly tailLightsTexColor: number,
    private readonly assetsPath: string,
  ) {
    const headlightsObjects: Mesh[] = [];
    // car model id 1 in gfx_car_tyre_textures
    this.frontTyresIgnoreMotion = assetsPath.includes('LDIABL.CFM');
    this.wheels = [null!, null!, null!, null!];
    this.frontWheels = [null!, null!];
    // for the wheels' depth bias: the body's widest |x|, the innermost |x| of each wheel and how far a steering morph
    // moves its vertices sideways
    let bodyHalfWidth = 0;
    const wheelInnerX = [Infinity, Infinity, Infinity, Infinity];
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
        const box = o.geometry.boundingBox!;
        wheelInnerX[wheelIndex] = Math.min(Math.abs(box.min.x + o.position.x), Math.abs(box.max.x + o.position.x));
        const wheelPos = Pnt3.avg(box.min, box.max);
        o.geometry!.translate(...Pnt3.spr(Pnt3.neg(wheelPos)));
        o.position.set(...Pnt3.spr(wheelPos));
        this.wheelIdlePositions[wheelIndex] = wheelPos;
      }
      if (
        o.morphTargetDictionary?.['left_turn'] !== undefined ||
        o.morphTargetDictionary?.['right_turn'] !== undefined
      ) {
        this.steerMorphMeshes.push(o);
        for (const target of o.geometry.morphAttributes['position'] ?? []) {
          for (let i = 0; i < target.count; i++) {
            this.steerMorphDx = Math.max(this.steerMorphDx, Math.abs(target.getX(i)));
          }
        }
        o.onBeforeRender = (_renderer, _scene, camera) => this.applySteerMorphs(o, camera);
      }
      if (wheelIndex < 0 && partitionOf(o) === 'inside') {
        for (const material of Array.isArray(o.material) ? o.material : [o.material]) {
          material.polygonOffset = true;
          material.polygonOffsetFactor = INSIDE_POLYGON_OFFSET;
          material.polygonOffsetUnits = INSIDE_POLYGON_OFFSET;
        }
      }
      if (wheelIndex < 0 && partitionOf(o) === 'surface') {
        if (!o.geometry.boundingBox) {
          o.geometry.computeBoundingBox();
        }
        const box = o.geometry.boundingBox!;
        bodyHalfWidth = Math.max(bodyHalfWidth, Math.abs(box.min.x + o.position.x), Math.abs(box.max.x + o.position.x));
      }
      if (o.name.includes('rsid') || o.name.includes('lite')) {
        headlightsObjects.push(o);
        this.originalTexWithTailLights = o.material.map;
      }
    });
    if (!this.originalTexWithTailLights) {
      throw new Error('Not a driveable NFS1 car');
    }
    if (this.wheelIdlePositions[1]) {
      this.leftSideSign = Math.sign(this.wheelIdlePositions[1].x) || 1;
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
    // the GLB's UVs, as its own (embedded, identical) tyre images: not flipped, unlike TextureLoader's default
    const loadTyres = (name: string) =>
      [1, 2, 3, 4].map(i => {
        const t = loader.load(`${assetsPath}/${name}${i}.png`);
        setupNfs1Texture(t);
        t.flipY = false;
        t.wrapS = ClampToEdgeWrapping;
        t.wrapT = ClampToEdgeWrapping;
        return t;
      });
    this.tyreTextures = loadTyres('tyr');
    // the outside partition: over the own body, see WHEEL_BIAS_MIN_SIN
    const gap = (wheels: number[]) => Math.max(0, ...wheels.map(i => bodyHalfWidth - wheelInnerX[i]));
    // turned by rotation (no morphs): the steering's allowance all the time
    this.frontWheelStraightGap = gap([0, 1]) + (this.steerMorphMeshes.length > 0 ? 0 : WHEEL_STEER_ROTATION_GAP);
    this.frontWheelGap.value = this.frontWheelStraightGap;
    this.rearWheelGap.value = gap([2, 3]);
    const tyreMaterial = (map: Texture, gap: { value: number }) => {
      const material = new MeshBasicMaterial({ map });
      material.transparent = true;
      material.alphaTest = 0.5;
      biasTowardCamera(material, gap);
      return material;
    };
    this.frontTyreMaterial = tyreMaterial(this.tyreTextures[0], this.frontWheelGap);
    this.rearTyreMaterial = tyreMaterial(this.tyreTextures[0], this.rearWheelGap);
    for (const [i, o] of this.wheels.entries()) {
      o.material = i < 2 ? this.frontTyreMaterial : this.rearTyreMaterial;
    }
  }

  async recolorTailLights(newColor: number) {
    if (!this.originalTexWithTailLights || !this.texWithTailLights || !this.texWithTailLightsImg) return;
    for (let i = 100; i > 0; i--) {
      if (!!this.originalTexWithTailLights.source.data) break;
      await sleep(50);
    }
    replaceColor(
      this.originalTexWithTailLights.source.data as HTMLImageElement,
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
    this.frontTyreMaterial?.dispose();
    this.frontTyreMaterial = null;
    this.rearTyreMaterial?.dispose();
    this.rearTyreMaterial = null;
  }
}
