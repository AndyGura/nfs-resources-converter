import { BoxGeometry, Mesh, MeshBasicMaterial, Object3D, Texture } from 'three';
import { TnfsCarColors, TnfsCarMeshController } from './tnfs-car-mesh-controller';

const CAR_COLORS: TnfsCarColors = {
  tail_lights: { texture_color: '#8cf818', textures: ['rsid'], off: '#3c0c0c', on: '#f81414' },
  light_bar: {
    texture_colors: ['#fc6454', '#fc0000', '#4c7cfc', '#0000fc'],
    textures: ['rear'],
    siren_colors: ['#fc0080', '#c00040', '#8000fc', '#4000c0'],
    siren_colors_swapped: ['#8000fc', '#4000c0', '#fc0080', '#c00040'],
    swap_interval_ms: 266.667,
  },
};

function carMesh(): Object3D {
  const car = new Object3D();
  for (const name of ['lbl__rt_frnt__tyr1', 'lbl__lt_frnt__tyr1', 'lbl__rt_rear__tyr1', 'lbl__lt_rear__tyr1']) {
    const wheel = new Mesh(new BoxGeometry(), new MeshBasicMaterial());
    wheel.name = name;
    car.add(wheel);
  }
  for (const name of ['rsid', 'rear']) {
    const material = new MeshBasicMaterial({ map: new Texture() });
    material.name = name;
    const body = new Mesh(new BoxGeometry(), material);
    body.name = name;
    car.add(body);
  }
  return car;
}

const replacements = (controller: TnfsCarMeshController, name: string): Map<number, number> =>
  (controller as any).replacementsOf(name);

describe('TnfsCarMeshController lights', () => {
  let controller: TnfsCarMeshController;

  beforeEach(() => {
    controller = new TnfsCarMeshController(carMesh(), CAR_COLORS, 'assets');
  });

  afterEach(() => controller.dispose());

  it('replaces the tail light color by the unlit or lit one', () => {
    expect(replacements(controller, 'rsid').get(0x8cf818)).toBe(0x3c0c0c);
    controller.tailLightsOn = true;
    expect(replacements(controller, 'rsid').get(0x8cf818)).toBe(0xf81414);
    expect(replacements(controller, 'rear').has(0x8cf818)).toBeFalse();
  });

  it('draws the light bar black, as the siren or as the texture', () => {
    expect(replacements(controller, 'rear').get(0xfc6454)).toBe(0);
    controller.lightBar = 'siren';
    expect(replacements(controller, 'rear').get(0xfc6454)).toBe(0xfc0080);
    controller.lightBar = 'texture';
    expect(replacements(controller, 'rear').has(0xfc6454)).toBeFalse();
    expect(replacements(controller, 'rsid').has(0xfc6454)).toBeFalse();
  });

  it('flashes only as the siren', () => {
    controller.sirenActive = true;
    controller.updateLights(300);
    expect(replacements(controller, 'rear').get(0xfc6454)).toBe(0);
    controller.lightBar = 'siren';
    expect(replacements(controller, 'rear').get(0xfc6454)).toBe(0xfc0080);
  });

  it('swaps the siren colors only while active', () => {
    controller.lightBar = 'siren';
    expect(replacements(controller, 'rear').get(0xfc6454)).toBe(0xfc0080);
    controller.updateLights(1000);
    expect(replacements(controller, 'rear').get(0xfc6454)).toBe(0xfc0080);
    controller.sirenActive = true;
    controller.updateLights(200);
    expect(replacements(controller, 'rear').get(0xfc6454)).toBe(0xfc0080);
    controller.updateLights(100);
    expect(replacements(controller, 'rear').get(0xfc6454)).toBe(0x8000fc);
    // two swaps in one update are no swap
    controller.updateLights(2 * 266.667);
    expect(replacements(controller, 'rear').get(0xfc6454)).toBe(0x8000fc);
    controller.sirenActive = false;
    controller.updateLights(1000);
    expect(replacements(controller, 'rear').get(0xfc6454)).toBe(0x8000fc);
  });

  it('has the lights of a model without wheels', () => {
    const noWheels = new TnfsCarMeshController(new Object3D(), CAR_COLORS, 'assets');
    expect(noWheels.hasWheels).toBeFalse();
    noWheels.tailLightsOn = true;
    noWheels.updateTyres(1000, 20, 0, 0, { x: 1, y: 0, z: 0 });
    noWheels.steeringAngle = 0.3;
    expect(replacements(noWheels, 'rsid').get(0x8cf818)).toBe(0xf81414);
    noWheels.dispose();
  });
});
