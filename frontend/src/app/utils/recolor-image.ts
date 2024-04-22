// consumes colors in RGB
export const recolorImage = (
  img: HTMLImageElement,
  colorToReplace: number,
  newColor: number,
  target: HTMLImageElement | null = null,
) => {
  const c = document.createElement('canvas');
  const ctx = c.getContext('2d')!;
  const w = img.width;
  const h = img.height;
  c.width = w;
  c.height = h;
  ctx.drawImage(img, 0, 0, w, h);
  const imageData = ctx.getImageData(0, 0, w, h);
  const [oldRed, oldGreen, oldBlue] = [colorToReplace >> 16, (colorToReplace >> 8) & 0xff, colorToReplace & 0xff];
  const [newRed, newGreen, newBlue] = [newColor >> 16, (newColor >> 8) & 0xff, newColor & 0xff];
  for (let i = 0; i < imageData.data.length; i += 4) {
    if (imageData.data[i] == oldRed && imageData.data[i + 1] == oldGreen && imageData.data[i + 2] == oldBlue) {
      imageData.data[i] = newRed;
      imageData.data[i + 1] = newGreen;
      imageData.data[i + 2] = newBlue;
    }
  }
  ctx.putImageData(imageData, 0, 0);
  (target || img).src = c.toDataURL('image/png');
  c.remove();
};
