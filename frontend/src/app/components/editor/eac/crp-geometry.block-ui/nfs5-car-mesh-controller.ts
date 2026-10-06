import { Box3, Mesh, Object3D, Vector3 } from 'three';

const WHEEL_SPIN_SPEED = { idle: 0, slow: 5, fast: 40 };

// mesh name: <article name>_LOD<lod>_ai<animation frame>[_<texture>][_damaged], with an optional duplicate suffix
// ".001", which three.js GLTFLoader turns into "001" (it strips dots and replaces spaces with underscores)
const NFS5_MESH_NAME_REGEX = /^(.*?)_LOD(\d+)_ai(\d+?)(?:\.?\d{3})?(?:_(.*?))?(_damaged)?(?:\.?\d{3})?(?:_\d+)?$/;

// wheel articles: "WheelFront", "WheelRear", alternative rims "WheelRear1", low LOD "TreadFront"
const NFS5_WHEEL_REGEX = /^(?:Wheel|Tread)(Front|Rear)\d*$/i;

// articles, which are never a part of the car exterior: driver (10 variants of body, arms, hands and legs), passenger,
// wheel shadow planes, cabrio roof (convertible top, its folded and unfolded states), race decals
const NFS5_HIDDEN_ARTICLES_REGEX =
  /^(?:DriverBody\d*|LODDriver\d*|(?:Left|Right)(?:Arm|Hand)\d*|Legs\d*|Passenger|WheelShadow.*|Cabrio.*|InteriorCabrio|DecalDoor.*|Decal.*R)$/i;

export type Nfs5MeshNameInfo = {
  article: string;
  lod: number;
  animationFrame: number;
  isDamaged: boolean;
};

/**
 * Animates NFS5 car model (*.crp) in preview: steers and spins wheels. Expects meshes, exported by CrpGeometrySerializer
 * for a car: "<article name>_LOD<lod>_ai<animation frame>[_<texture>][_damaged]", X left, Y backward (the car front is
 * at -Y), Z up. With `turnToYForward` the model is turned around (meshes' geometry is modified), so it is X right,
 * Y forward, Z up, like other car mesh controllers expect.
 *
 * A CRP car has every variant of every part: body kits ("Body", "Body1", "Body2"), spoiler states, cabrio roof, 10
 * drivers, animation frames and damaged copies of all of them. Which variants are used is defined by the style in
 * car's .tpg file, which slots cannot be mapped to articles yet. `isDefaultExteriorMesh` picks a plausible default
 * car look by article names instead. Depends only on three.js, so it can be reused outside the GUI
 */
export class Nfs5CarMeshController {
  private wheels: { meshes: Mesh[]; isFront: boolean }[] = [];
  private spinAngle = 0;
  private animationTimer: any = null;
  // the car front is at -Y: wheels roll forward around +X
  private readonly spinSign: number;

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
        this.spinAngle += (this.spinSign * WHEEL_SPIN_SPEED[this._speed]) / 60;
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

  get hasWheels(): boolean {
    return this.wheels.length > 0;
  }

  constructor(mesh: Object3D, turnToYForward: boolean = false) {
    this.spinSign = turnToYForward ? -1 : 1;
    if (turnToYForward) {
      mesh.traverse(o => {
        if (o instanceof Mesh) {
          o.geometry.rotateZ(Math.PI);
          o.position.applyAxisAngle(new Vector3(0, 0, 1), Math.PI);
        }
      });
    }
    // wheel meshes by article name, LOD and side
    const wheels: { [key: string]: { meshes: Mesh[]; isFront: boolean } } = {};
    mesh.traverse(o => {
      if (!(o instanceof Mesh)) {
        return;
      }
      const info = Nfs5CarMeshController.parseMeshName(o.name);
      const match = info && NFS5_WHEEL_REGEX.exec(info.article);
      if (!info || !match) {
        return;
      }
      o.geometry.computeBoundingBox();
      const center = o.geometry.boundingBox!.getCenter(new Vector3()).add(o.position);
      const key = `${info.article}_${info.lod}_${info.animationFrame}_${info.isDamaged}_${center.x > 0}`;
      (wheels[key] = wheels[key] || { meshes: [], isFront: match[1].toLowerCase() === 'front' }).meshes.push(o);
    });
    for (const wheel of Object.values(wheels)) {
      // move pivot to the wheel center, so it rotates in place
      const box = new Box3();
      for (const m of wheel.meshes) {
        box.union(m.geometry.boundingBox!.clone().translate(m.position));
      }
      const center = box.getCenter(new Vector3());
      for (const m of wheel.meshes) {
        m.geometry.translate(m.position.x - center.x, m.position.y - center.y, m.position.z - center.z);
        m.position.copy(center);
        m.rotation.order = 'ZXY';
      }
      this.wheels.push(wheel);
    }
  }

  static parseMeshName(name: string): Nfs5MeshNameInfo | null {
    const match = NFS5_MESH_NAME_REGEX.exec(name);
    if (!match) {
      return null;
    }
    return {
      // article names can have trailing spaces ("Light2 "), which become underscores in three.js
      article: match[1].replace(/[\s_]+$/, ''),
      lod: +match[2],
      animationFrame: +match[3],
      isDamaged: !!match[5],
    };
  }

  /**
   * Returns a filter of meshes, which form the default exterior of the car: the most detailed LOD, the first
   * animation frame, not damaged, without driver and cabrio roof, without alternative variants of parts (an article,
   * named as another article plus a number or a letter, e.g. "Body1", "Light2a", is a variant of it), spoiler down
   */
  static defaultExteriorFilter(meshNames: string[]): (name: string) => boolean {
    const infos = meshNames.map(x => Nfs5CarMeshController.parseMeshName(x)).filter(x => !!x) as Nfs5MeshNameInfo[];
    const minLod = Math.min(...infos.map(x => x.lod));
    const isDefaultArticle = Nfs5CarMeshController.defaultArticleFilter(infos.map(x => x.article));
    return (name: string) => {
      const info = Nfs5CarMeshController.parseMeshName(name);
      return (
        !!info && info.lod === minLod && info.animationFrame === 0 && !info.isDamaged && isDefaultArticle(info.article)
      );
    };
  }

  /** Like `defaultExteriorFilter`, but only by article names: for any LOD, animation frame and damage */
  static defaultArticleFilter(allArticles: string[]): (article: string) => boolean {
    const articles = new Set(allArticles.map(x => x.toLowerCase()));
    const hasSpoilerDown = [...articles].some(x => x === 'spoiler' || x.startsWith('spoilerdown'));
    const isVariant = (article: string) =>
      [/^(.*\D)\d+$/, /^(.*\d)[a-z]$/].some(regex => {
        const base = regex.exec(article)?.[1];
        return !!base && articles.has(base.toLowerCase());
      });
    return (article: string) =>
      !NFS5_HIDDEN_ARTICLES_REGEX.test(article) &&
      !/^SpoilerUp/i.test(article) &&
      !(hasSpoilerDown && /^SpoilerW/i.test(article)) &&
      !isVariant(article);
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
