import { BoxGeometry, Group, Mesh, MeshBasicMaterial } from 'three';
import { Nfs5CarMeshController } from './nfs5-car-mesh-controller';

function mesh(name: string, x: number, y: number, z: number): Mesh {
  const geometry = new BoxGeometry(0.2, 0.6, 0.6);
  geometry.translate(x, y, z);
  const result = new Mesh(geometry, new MeshBasicMaterial());
  result.name = name;
  return result;
}

describe('Nfs5CarMeshController', () => {
  it('parses mesh names, exported by CrpGeometrySerializer and renamed by three.js', () => {
    expect(Nfs5CarMeshController.parseMeshName('Body1_LOD2_ai0_page_4_alpha_damaged')).toEqual({
      article: 'Body1',
      lod: 2,
      animationFrame: 0,
      isDamaged: true,
    });
    expect(Nfs5CarMeshController.parseMeshName('RightArm1_LOD1_ai12')?.animationFrame).toBe(12);
    // Blender duplicate suffix ".001", dot removed by GLTFLoader
    expect(Nfs5CarMeshController.parseMeshName('DoorIn_LOD2_ai0001')?.animationFrame).toBe(0);
    expect(Nfs5CarMeshController.parseMeshName('DoorIn_LOD2_ai0.001')?.animationFrame).toBe(0);
    // trailing space of article name, replaced by GLTFLoader
    expect(Nfs5CarMeshController.parseMeshName('Light2__LOD1_ai0_page_0')?.article).toBe('Light2');
    expect(Nfs5CarMeshController.parseMeshName('shadow')).toBeNull();
  });

  it('picks default exterior meshes', () => {
    const names = [
      'Body_LOD1_ai0_page_0',
      'Body_LOD2_ai0_page_0',
      'Body_LOD1_ai0_page_0_damaged',
      'Body1_LOD1_ai0_page_0',
      'Light2_LOD1_ai0_page_0',
      'Light2a_LOD1_ai0_page_0',
      'Wiper1a_LOD1_ai0_page_3',
      'SpoilerDown_LOD1_ai0_page_0',
      'SpoilerUp_LOD1_ai0_page_0',
      'SpoilerW_LOD1_ai0_page_0',
      'DriverBody1_LOD1_ai0',
      'Cabrio_LOD1_ai1_page_0',
      'WheelFront_LOD1_ai0_page_3_alpha',
    ];
    const isDefault = Nfs5CarMeshController.defaultExteriorFilter(names);
    expect(names.filter(isDefault)).toEqual([
      'Body_LOD1_ai0_page_0',
      'Light2_LOD1_ai0_page_0',
      'Wiper1a_LOD1_ai0_page_3',
      'SpoilerDown_LOD1_ai0_page_0',
      'WheelFront_LOD1_ai0_page_3_alpha',
    ]);
  });

  it('finds wheels and turns the car to Y forward', () => {
    const car = new Group();
    car.add(
      // front is at -Y
      mesh('WheelFront_LOD1_ai0_page_3_alpha', -0.7, -1.2, 0.3),
      mesh('WheelFront_LOD1_ai0_page_3_alpha001', 0.7, -1.2, 0.3),
      mesh('WheelRear_LOD1_ai0_page_3_alpha', 0.7, 1.2, 0.3),
      mesh('Body_LOD1_ai0_page_0', 0, 0, 0.5),
    );
    const controller = new Nfs5CarMeshController(car, true);
    expect(controller.hasWheels).toBeTrue();
    const frontWheel = car.getObjectByName('WheelFront_LOD1_ai0_page_3_alpha')!;
    // pivot is moved to the wheel center, which is turned around
    expect(frontWheel.position.x).toBeCloseTo(0.7);
    expect(frontWheel.position.y).toBeCloseTo(1.2);
    expect(frontWheel.position.z).toBeCloseTo(0.3);
    controller.steeringAngle = 0.3;
    expect(frontWheel.rotation.z).toBeCloseTo(0.3);
    expect(car.getObjectByName('WheelRear_LOD1_ai0_page_3_alpha')!.rotation.z).toBeCloseTo(0);
    controller.dispose();
  });
});
