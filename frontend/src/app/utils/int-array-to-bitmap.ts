export function intArrayToBitmap(arr: number[], width: number, height: number, depth: number = 32): string {
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext('2d', { alpha: true })!;
  context.imageSmoothingEnabled = false;
  const imgData = context.createImageData(width, height);
  for (let i = 0; i < arr.length; i++) {
    const color = arr[i];
    imgData.data[i*4] = color >>> 24;
    imgData.data[i*4+1] = (color & 0xff0000) >> 16;
    imgData.data[i*4+2] = (color & 0xff00) >> 8;
    imgData.data[i*4+3] = color & 0xff;
  }
  context.putImageData(imgData, 0, 0);
  const dataUrl = canvas.toDataURL();
  canvas.remove();
  return dataUrl;
}
