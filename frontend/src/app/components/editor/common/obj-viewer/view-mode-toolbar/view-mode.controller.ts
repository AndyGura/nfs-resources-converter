import {
  AmbientLight,
  BufferGeometry,
  EdgesGeometry,
  LineBasicMaterial,
  LineSegments,
  Material,
  Mesh,
  MeshBasicMaterial,
  MeshLambertMaterial,
  MeshPhongMaterial,
  MeshStandardMaterial,
  Object3D,
} from 'three';

export type ViewMode = 'material' | 'wireframe' | 'unlit' | 'edges';

export class ViewModeController {
  private _viewMode: ViewMode = 'material';
  private originalMaterials: Map<Mesh, Material | Material[]> = new Map();
  private edgeLines: LineSegments[] = [];
  private meshesWithViewModeMaterials: Set<Mesh> = new Set();
  private controllerManagedMaterials: Map<Mesh, Material | Material[]> = new Map();
  private onChildAddedBound: (event: any) => void;
  private onChildRemovedBound: (event: any) => void;

  constructor(
    private rootObject: Object3D,
    private ambientLight: AmbientLight,
  ) {
    this.captureOriginalMaterials();
    this.onChildAddedBound = this.onChildAdded.bind(this);
    this.onChildRemovedBound = this.onChildRemoved.bind(this);
    this.rootObject.addEventListener('childadded', this.onChildAddedBound);
    this.rootObject.addEventListener('childremoved', this.onChildRemovedBound);
  }

  get listViewModes(): ViewMode[] {
    return ['material', 'wireframe', 'unlit', 'edges'];
  }

  get viewMode(): ViewMode {
    return this._viewMode;
  }

  setViewMode(mode: ViewMode): void {
    this._viewMode = mode;
    this.applyViewMode();
  }

  private captureOriginalMaterials(): void {
    this.originalMaterials.clear();
    this.rootObject.traverse((obj: Object3D) => {
      if (obj instanceof Mesh) {
        this.originalMaterials.set(obj, Array.isArray(obj.material) ? [...obj.material] : obj.material.clone());
      }
    });
  }

  private clearEdgeLines(): void {
    if (this.edgeLines.length > 0) {
      for (const edgeLine of this.edgeLines) {
        if (edgeLine.parent) {
          edgeLine.parent.remove(edgeLine);
        }
        edgeLine.geometry.dispose();
        (edgeLine.material as LineBasicMaterial).dispose();
      }
    }
    this.edgeLines = [];
  }

  public applyViewMode(): void {
    this.clearEdgeLines();
    this.applyViewModeToTree(this.rootObject);
  }

  private applyViewModeToTree(root: Object3D): void {
    root.traverse((obj: Object3D) => {
      if (obj instanceof Mesh) {
        this.applyViewModeToMesh(obj);
      }
    });
  }

  private applyViewModeToMesh(obj: Mesh): void {
    const originalMaterial = this.originalMaterials.get(obj);
    if (!originalMaterial) {
      // If we found a mesh that wasn't there before, capture its material
      this.originalMaterials.set(obj, Array.isArray(obj.material) ? [...obj.material] : obj.material.clone());
    }

    switch (this._viewMode) {
      case 'material':
        if (this.meshesWithViewModeMaterials.has(obj)) {
          const storedMaterial = this.controllerManagedMaterials.get(obj);
          if (storedMaterial) {
            obj.material = storedMaterial;
            this.controllerManagedMaterials.delete(obj);
          }
          this.meshesWithViewModeMaterials.delete(obj);
        }
        this.ambientLight.intensity = 2;
        break;
      case 'wireframe':
        if (!this.meshesWithViewModeMaterials.has(obj)) {
          this.controllerManagedMaterials.set(obj, obj.material);
        }
        const currentMaterial = this.controllerManagedMaterials.get(obj) || obj.material;
        const wireframeMaterials = Array.isArray(currentMaterial) ? currentMaterial : [currentMaterial];
        const newWireframeMaterials = wireframeMaterials.map(mat => {
          return new MeshBasicMaterial({
            color: mat instanceof MeshBasicMaterial ? mat.color : 0xffffff,
            wireframe: true,
            transparent: true,
            opacity: 0.8,
          });
        });
        obj.material = newWireframeMaterials.length === 1 ? newWireframeMaterials[0] : newWireframeMaterials;
        this.meshesWithViewModeMaterials.add(obj);
        this.ambientLight.intensity = 2;
        break;
      case 'unlit':
        if (!this.meshesWithViewModeMaterials.has(obj)) {
          this.controllerManagedMaterials.set(obj, obj.material);
        }
        const currentUnlitMaterial = this.controllerManagedMaterials.get(obj) || obj.material;
        const unlitMaterials = Array.isArray(currentUnlitMaterial) ? currentUnlitMaterial : [currentUnlitMaterial];
        const newUnlitMaterials = unlitMaterials.map(mat => {
          let textureMap = null;
          let materialColor = 0xffffff;
          if (mat instanceof MeshBasicMaterial) {
            textureMap = mat.map;
            materialColor = mat.color.getHex();
          } else if (mat instanceof MeshLambertMaterial) {
            textureMap = mat.map;
            materialColor = mat.color.getHex();
          } else if (mat instanceof MeshStandardMaterial) {
            textureMap = mat.map;
            materialColor = mat.color.getHex();
          } else if (mat instanceof MeshPhongMaterial) {
            textureMap = mat.map;
            materialColor = mat.color.getHex();
          }
          const unlitMat = new MeshBasicMaterial({
            color: materialColor,
            map: textureMap,
            transparent: mat.transparent,
            opacity: mat.opacity,
            side: mat.side,
          });
          return unlitMat;
        });
        obj.material = newUnlitMaterials.length === 1 ? newUnlitMaterials[0] : newUnlitMaterials;
        this.meshesWithViewModeMaterials.add(obj);
        this.ambientLight.intensity = 0;
        break;
      case 'edges':
        if (this.meshesWithViewModeMaterials.has(obj)) {
          const storedMaterial = this.controllerManagedMaterials.get(obj);
          if (storedMaterial) {
            obj.material = storedMaterial;
            this.controllerManagedMaterials.delete(obj);
          }
          this.meshesWithViewModeMaterials.delete(obj);
        }
        this.ambientLight.intensity = 2;

        const edges = new EdgesGeometry(obj.geometry as BufferGeometry);
        const edgeMaterial = new LineBasicMaterial({ color: 0x000000, linewidth: 2 });
        const edgeLines = new LineSegments(edges, edgeMaterial);
        obj.add(edgeLines);
        this.edgeLines.push(edgeLines);
        break;
    }
  }

  private onChildAdded(event: any): void {
    this.applyViewModeToTree(event.child);
  }

  private onChildRemoved(event: any): void {
    event.child.traverse((obj: Object3D) => {
      if (obj instanceof Mesh) {
        this.originalMaterials.delete(obj);
        this.controllerManagedMaterials.delete(obj);
        this.meshesWithViewModeMaterials.delete(obj);
      }
    });
  }

  public dispose(): void {
    this.rootObject.removeEventListener('childadded', this.onChildAddedBound);
    this.rootObject.removeEventListener('childremoved', this.onChildRemovedBound);
    this.clearEdgeLines();
    this.originalMaterials.clear();
    this.controllerManagedMaterials.clear();
    this.meshesWithViewModeMaterials.clear();
  }
}
