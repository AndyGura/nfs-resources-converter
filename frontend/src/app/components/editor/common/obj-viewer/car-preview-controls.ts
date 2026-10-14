import { ObjViewerControl } from './obj-viewer.component';

// wheel speed slider, as nfs-web's /car-tex-debug: exponential, fine at low speeds (the TNFS tyre textures change at
// 0.1, 10 and 30 m/s), up to a bit over the fastest cars' top speed
const MAX_WHEEL_SPEED = 100;
const SPEED_SLIDER_CURVE = 4;
const MPS_TO_MPH = 3600 / 1609.344;

const sliderSpeed = (t: number) =>
  (MAX_WHEEL_SPEED * (Math.exp(SPEED_SLIDER_CURVE * t) - 1)) / (Math.exp(SPEED_SLIDER_CURVE) - 1);

/** Car preview's wheel speed slider, `change` gets the speed in m/s */
export const wheelSpeedControl = (change: (speed: number) => void): ObjViewerControl => ({
  label: 'Wheel speed',
  type: 'slider',
  minValue: 0,
  maxValue: 1,
  valueStep: 0.001,
  value: 0,
  format: t => {
    const speed = sliderSpeed(t);
    return `${speed.toFixed(1)} m/s, ${(speed * MPS_TO_MPH).toFixed(0)} mph`;
  },
  change: t => change(sliderSpeed(t)),
});

/** Car preview's steering slider, `change` gets the front wheels' angle in radians */
export const steeringControl = (change: (angle: number) => void): ObjViewerControl => ({
  label: 'Steering angle',
  type: 'slider',
  minValue: -0.7,
  maxValue: 0.7,
  valueStep: 0.05,
  value: 0,
  change,
});
