export const fileFormatIcon = (blockClassStr: string): string => {
  for (const className of blockClassStr.split('__')) {
    if (iconMap[className]) {
      return iconMap[className];
    }
  }
  return fallbackIcon;
};

const iconMap: Record<string, string> = {
  FfnFont: 'text_fields',

  EacImage: 'image',

  EacPalette: 'palette',

  BytesBlock: 'data_object',

  ShpiBlock: 'photo_library',

  WwwwBlock: 'archive',
  BigfBlock: 'archive',
  RefPackBlock: 'archive',
  Qfs2Block: 'archive',
  Qfs3Block: 'archive',

  OripGeometry: 'view_in_ar',
  GeoGeometry: 'view_in_ar',
  CrpGeometry: 'view_in_ar',

  TriMap: 'layers',
  TrkMap: 'layers',
  FrdMap: 'layers',

  EacsAudioFile: 'audiotrack',
};
const fallbackIcon = 'question_mark';
