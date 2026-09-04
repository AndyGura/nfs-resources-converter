export type GeneralConfig = {
  blender_executable: string;
  ffmpeg_executable: string;
  print_blender_log: boolean;
  recent_files: string[];
  show_hidden_fields: boolean;
};

export type ConversionConfig = {
  multiprocess_processes_count: number;
  input_path: string;
  output_path: string;
  images__save_image_positions: boolean;
  images__save_palettes: boolean;
  images__save_mipmaps: boolean;
  images__save_embedded_palette: boolean;
  images__save_texts: boolean;
  maps__save_as_chunked: boolean;
  maps__save_invisible_wall_collisions: boolean;
  maps__save_terrain_collisions: boolean;
  maps__save_spherical_skybox_texture: boolean;
  maps__add_props_to_obj: boolean;
  geometry__save_obj: boolean;
  geometry__save_blend: boolean;
  geometry__export_to_gg_web_engine: boolean;
};
