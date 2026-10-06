import { BoxGeometry, Group, Mesh, MeshBasicMaterial, Texture } from 'three';
import { Nfs6CarMeshController } from './nfs6-car-mesh-controller';

function mesh(name: string, x: number, y: number, z: number, material = new MeshBasicMaterial()): Mesh {
  const geometry = new BoxGeometry(0.2, 0.6, 0.6);
  geometry.translate(x, y, z);
  const result = new Mesh(geometry, material);
  result.name = name;
  return result;
}

describe('Nfs6CarMeshController', () => {
  let car: Group;
  let paint: MeshBasicMaterial;

  beforeEach(() => {
    car = new Group();
    paint = new MeshBasicMaterial({ map: new Texture() });
    paint.name = 'skin';
    car.add(
      mesh('hp_4_ALPHA_OPAQUE_HOODShape', 0, 1.5, 0.3, paint),
      // front right and rear left wheels
      mesh('hp_6_ALPHA_OPAQUE_RUBBER_Shape', 0.8, 1.1, 0.2),
      mesh('hp_8_ALPHA_OPAQUE_RUBBER_Shape2', -0.8, -1.6, 0.2),
      mesh('hp_18_ALPHA_OPAQUE_BRAKE_2Shape', 0.85, 1.2, 0.1),
    );
  });

  it('finds wheels and brakes', () => {
    const controller = new Nfs6CarMeshController(car, [], []);
    expect(controller.hasWheels).toBeTrue();
    const wheel = car.getObjectByName('hp_6_ALPHA_OPAQUE_RUBBER_Shape')!;
    // pivot is moved to the wheel center
    expect(wheel.position.x).toBeCloseTo(0.8);
    expect(wheel.position.y).toBeCloseTo(1.1);
    expect(wheel.position.z).toBeCloseTo(0.2);
    // brake caliper turns around its wheel axis
    const brake = car.getObjectByName('hp_18_ALPHA_OPAQUE_BRAKE_2Shape')!;
    expect(brake.position.x).toBeCloseTo(0.85);
    expect(brake.position.y).toBeCloseTo(1.1);
    expect(brake.position.z).toBeCloseTo(0.2);
  });

  it('steers front wheels and brakes only', () => {
    const controller = new Nfs6CarMeshController(car, [], []);
    controller.steeringAngle = 0.5;
    expect(car.getObjectByName('hp_6_ALPHA_OPAQUE_RUBBER_Shape')!.rotation.z).toBeCloseTo(0.5);
    expect(car.getObjectByName('hp_18_ALPHA_OPAQUE_BRAKE_2Shape')!.rotation.z).toBeCloseTo(0.5);
    expect(car.getObjectByName('hp_8_ALPHA_OPAQUE_RUBBER_Shape2')!.rotation.z).toBe(0);
    expect(car.getObjectByName('hp_4_ALPHA_OPAQUE_HOODShape')!.rotation.z).toBe(0);
  });

  it('shows light bones', () => {
    const controller = new Nfs6CarMeshController(
      car,
      [
        { name: 'LIGHT_TAIL_LEFT1', position: [-0.5, -2.1, 0.2] },
        { name: 'EXHAUST_1', position: [-0.2, -2.1, -0.2] },
      ],
      [],
    );
    expect(controller.hasLights).toBeTrue();
    expect(controller.showLights).toBeFalse();
    controller.showLights = true;
    const light = car.getObjectByName('LIGHT_TAIL_LEFT1')!;
    expect(light.position.toArray()).toEqual([-0.5, -2.1, 0.2]);
    expect(car.getObjectByName('EXHAUST_1')).toBeUndefined();
  });

  it('has default skin when the model uses skin texture', () => {
    const skins = [
      { name: 'skin00', label: 'red', texture: 'textures/skins/skin00-skin.png' },
      { name: 'skin01', label: 'black', texture: 'textures/skins/skin01-skin.png' },
    ];
    expect(new Nfs6CarMeshController(car, [], skins).skin).toBe('skin00');
    paint.name = 'other';
    expect(new Nfs6CarMeshController(new Group().add(mesh('hp_0_X', 0, 0, 0, paint)), [], skins).skin).toBeNull();
  });
});
