// consumes colors in RGB
export const replaceColor = (
  img: HTMLImageElement,
  colorToReplace: number,
  newColor: number,
  target: HTMLImageElement | null = null,
) => {
  const [oldRed, oldGreen, oldBlue] = [colorToReplace >> 16, (colorToReplace >> 8) & 0xff, colorToReplace & 0xff];
  const [newRed, newGreen, newBlue] = [newColor >> 16, (newColor >> 8) & 0xff, newColor & 0xff];
  return recolorImageSmart(
    img,
    (data, i) => {
      if (data[i] == oldRed && data[i + 1] == oldGreen && data[i + 2] == oldBlue) {
        data[i] = newRed;
        data[i + 1] = newGreen;
        data[i + 2] = newBlue;
      }
    },
    target,
  );
};

export const recolorImageSmart = (
  img: HTMLImageElement,
  func: (data: Uint8ClampedArray, index: number) => void,
  target: HTMLImageElement | null = null,
) => {
  const c = document.createElement('canvas');
  const ctx = c.getContext('2d', { willReadFrequently: true })!;
  const w = img.width;
  const h = img.height;
  c.width = w;
  c.height = h;
  ctx.drawImage(img, 0, 0, w, h);
  const imageData = ctx.getImageData(0, 0, w, h);
  for (let i = 0; i < imageData.data.length; i += 4) {
    func(imageData.data, i);
  }
  ctx.putImageData(imageData, 0, 0);
  (target || img).src = c.toDataURL('image/png');
  c.remove();
};
