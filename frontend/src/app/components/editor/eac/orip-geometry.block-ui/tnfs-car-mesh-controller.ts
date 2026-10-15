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
import { recolorImageSmart } from '../../../../utils/recolor-image';

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

/**
 * `car_colors.json` the converter writes next to the textures of a TNFS car model (CFM): colors of the PNGs (`#rrggbb`)
 * that stand for palette indices the game draws in other colors (Win95 SE gfx_draw_car_model 0x458d4c,
 * gfx_shpi_remap_to_vga_palette 0x4470e0), and the textures having them. The same keys for every car: which role a car
 * has (a cop) is up to the game. The converter keeps these PNG colors unique
 */
export interface TnfsCarColors {
  /** colors the car's `!xxx` gives to its entries of the game's 256-color palette in 8-bit modes, not for the textures */
  palette_slice?: string[];
  /** index 254: the car's tail light palette entry, `on` while braking */
  tail_lights?: { texture_color: string; textures: string[]; off: string; on: string };
  /**
   * indices 250..253: a cop's light bar, `siren_colors` and `siren_colors_swapped` alternate during a police chase;
   * other cars have them black
   */
  light_bar?: {
    texture_colors: string[];
    textures: string[];
    siren_colors: string[];
    siren_colors_swapped: string[];
    swap_interval_ms: number;
  };
}

/** How indices 250..253 are drawn: black (as the game does on cars), the cop's light bar, or as in the PNGs */
export type TnfsLightBarMode = 'black' | 'siren' | 'texture';

const hexColor = (color: string) => parseInt(color.substring(1), 16);

/** A copy of a car texture with some colors replaced (see TnfsCarColors), given to `onReady` once first drawn */
class RecoloredTexture {
  readonly texture: Texture;
  private readonly img: HTMLImageElement = document.createElement('img');
  private version = 0;
  private ready = false;

  constructor(
    readonly name: string,
    private readonly original: Texture,
    onReady: (texture: Texture) => void,
  ) {
    this.texture = new Texture(this.img);
    this.texture.name = original.name;
    this.texture.flipY = original.flipY;
    this.texture.wrapS = original.wrapS;
    this.texture.wrapT = original.wrapT;
    setupNfs1Texture(this.texture);
    this.img.onload = () => {
      this.texture.needsUpdate = true;
      if (!this.ready) {
        this.ready = true;
        onReady(this.texture);
      }
    };
  }

  /** Redraws the copy: the original with these colors (0xRRGGBB) replaced */
  async recolor(replacements: Map<number, number>) {
    const version = ++this.version;
    for (let i = 100; i > 0 && !this.original.source.data; i--) {
      await sleep(50);
    }
    // the original never loaded, or a later call redraws it
    if (!this.original.source.data || version !== this.version) return;
    recolorImageSmart(
      this.original.source.data as HTMLImageElement,
      (data, i) => {
        const color = replacements.get((data[i] << 16) | (data[i + 1] << 8) | data[i + 2]);
        if (color !== undefined) {
          data[i] = color >> 16;
          data[i + 1] = (color >> 8) & 0xff;
          data[i + 2] = color & 0xff;
        }
      },
      this.img,
    );
  }

  dispose() {
    this.version++;
    this.img.onload = null;
    this.img.remove();
    this.texture.dispose();
  }
}

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
  frontTyreMaterial: MeshBasicMaterial | null = null;
  rearTyreMaterial: MeshBasicMaterial | null = null;

  // the textures with colors of carColors, see recolor
  private readonly recoloredTextures: RecoloredTexture[] = [];
  // time to the next swap of the siren colors, and whether they are swapped now
  private sirenTime = 0;
  private sirenSwapped = false;
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

  // the model has the four wheels (labels lt_frnt, rt_frnt, lt_rear, rt_rear): the tyres and the steering work
  public readonly hasWheels: boolean;
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
    this.recolor(this.carColors?.tail_lights?.textures);
  }

  private _sirenActive: boolean = false;
  get sirenActive(): boolean {
    return this._sirenActive;
  }

  /**
   * The cop's light bar flashes (police chase, lightBar 'siren'): its colors swap every `swap_interval_ms` in
   * updateLights. When it stops, they stay as they are, as in the game
   */
  set sirenActive(value: boolean) {
    if (value === this._sirenActive) return;
    this._sirenActive = value;
    this.sirenTime = 0;
  }

  private _lightBar: TnfsLightBarMode = 'black';
  get lightBar(): TnfsLightBarMode {
    return this._lightBar;
  }

  /** How indices 250..253 are drawn: 'black' for cars, 'siren' for a cop (see sirenActive), 'texture' as in the PNGs */
  set lightBar(value: TnfsLightBarMode) {
    if (value === this._lightBar) return;
    this._lightBar = value;
    this.recolor(this.carColors?.light_bar?.textures);
  }

  /** Lights over time (the siren), once per frame */
  updateLights(deltaMs: number): void {
    const lightBar = this.carColors?.light_bar;
    if (!lightBar || !this._sirenActive || this._lightBar !== 'siren') {
      return;
    }
    this.sirenTime += deltaMs;
    if (this.sirenTime < lightBar.swap_interval_ms) {
      return;
    }
    // swaps twice in a long stall are no swap
    const swaps = Math.floor(this.sirenTime / lightBar.swap_interval_ms);
    this.sirenTime -= swaps * lightBar.swap_interval_ms;
    if (swaps % 2) {
      this.sirenSwapped = !this.sirenSwapped;
      this.recolor(lightBar.textures);
    }
  }

  /** The colors of a texture to replace now: PNG color -> color */
  private replacementsOf(name: string): Map<number, number> {
    const result = new Map<number, number>();
    const { tail_lights, light_bar }: TnfsCarColors = this.carColors ?? {};
    if (tail_lights?.textures.includes(name)) {
      result.set(hexColor(tail_lights.texture_color), hexColor(this._tailLightsOn ? tail_lights.on : tail_lights.off));
    }
    if (light_bar?.textures.includes(name) && this._lightBar !== 'texture') {
      const colors = this.sirenSwapped ? light_bar.siren_colors_swapped : light_bar.siren_colors;
      light_bar.texture_colors.forEach((c, i) =>
        result.set(hexColor(c), this._lightBar === 'siren' ? hexColor(colors[i]) : 0),
      );
    }
    return result;
  }

  /** Redraws the recolored textures of these names (all without names) */
  private recolor(names?: string[]) {
    for (const texture of this.recoloredTextures) {
      if (!names || names.includes(texture.name)) {
        texture.recolor(this.replacementsOf(texture.name)).then();
      }
    }
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
    if (!this.frontTyreMaterial || !this.rearTyreMaterial) {
      return;
    }
    if (force || front !== this.frontTyreIndex) {
      this.frontTyreIndex = front;
      this.frontTyreMaterial.map = this.tyreTextures[front];
      this.frontTyreMaterial.needsUpdate = true;
    }
    if (force || rear !== this.rearTyreIndex) {
      this.rearTyreIndex = rear;
      this.rearTyreMaterial.map = this.tyreTextures[rear];
      this.rearTyreMaterial.needsUpdate = true;
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
    private readonly carColors: TnfsCarColors | null,
    private readonly assetsPath: string,
  ) {
    const { tail_lights, light_bar }: TnfsCarColors = carColors ?? {};
    const recoloredNames = new Set([...(tail_lights?.textures || []), ...(light_bar?.textures || [])]);
    // materials of the body by texture name (the OBJ's are named as their texture, the GLB's textures are)
    const recoloredMaterials = new Map<string, MeshBasicMaterial[]>();
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
      if (wheelIndex < 0) {
        for (const material of Array.isArray(o.material) ? o.material : [o.material]) {
          // any material with a texture (the GUI's OBJ ones are MeshPhongMaterial)
          const map = (material as MeshBasicMaterial).map;
          const name = map && (map.name || material.name);
          if (name && recoloredNames.has(name)) {
            recoloredMaterials.set(name, [...(recoloredMaterials.get(name) || []), material as MeshBasicMaterial]);
          }
        }
      }
    });
    // no wheels: a model without the wheel labels (COPMUST, low-poly models), only the lights work
    this.hasWheels = this.wheels.every(wheel => !!wheel);
    if (!this.hasWheels) {
      this.wheels = [];
      this.frontWheels = [];
    }
    if (this.wheelIdlePositions[1]) {
      this.leftSideSign = Math.sign(this.wheelIdlePositions[1].x) || 1;
    }

    for (const [name, materials] of recoloredMaterials) {
      // the copy replaces the original once drawn
      this.recoloredTextures.push(
        new RecoloredTexture(name, materials[0].map!, texture => {
          for (const material of materials) {
            material.map = texture;
            material.needsUpdate = true;
          }
        }),
      );
    }
    if (!this.hasWheels) {
      this.recolor();
      return;
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
    // the game remaps the tyre textures too (light bar colors black)
    this.tyreTextures.forEach((original, i) => {
      if (recoloredNames.has(`tyr${i + 1}`)) {
        this.recoloredTextures.push(
          new RecoloredTexture(`tyr${i + 1}`, original, texture => {
            this.tyreTextures[i] = texture;
            this.setTyreIndices(this.frontTyreIndex, this.rearTyreIndex, true);
          }),
        );
      }
    });
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
    this.recolor();
  }

  public dispose() {
    for (const texture of this.recoloredTextures) {
      texture.dispose();
    }
    this.recoloredTextures.length = 0;
    this.frontTyreMaterial?.dispose();
    this.frontTyreMaterial = null;
    this.rearTyreMaterial?.dispose();
    this.rearTyreMaterial = null;
  }
}
