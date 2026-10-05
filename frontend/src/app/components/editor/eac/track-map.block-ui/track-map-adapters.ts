import { MapGraph, MapGraphNodeType, Point3 } from '@gg-web-engine/core';
import { ClampToEdgeWrapping, RepeatWrapping, Texture } from 'three';
import { nfs6Route } from './nfs6-route';
import { setupNfs1Texture } from '../../common/obj-viewer/obj-viewer.component';
import { BlockData } from '../../types';
import type { TrackEntity, TrackMapWorldEntity } from './track-map-world.entity';
import { loadTnfsChunkProps } from './tnfs-track-props';

// A road spline point in game coordinates (Y up); orientation is the heading in radians
export interface TrackSplinePoint {
  position: Point3;
  orientation: number;
}

// A panel showing the part of a data array that belongs to the selected spline point:
// entry index = spline index / itemsPerEntry
export interface TrackSplineDetailPanel {
  title: string;
  field: string;
  itemsPerEntry: number;
}

// Chunk positions, road spline and loop flag of a track
export interface TrackLayout {
  // null: positions come from `terrain_chunks.json`
  chunkPositions: Point3[] | null;
  splinePoints: TrackSplinePoint[];
  isClosed: boolean;
}

// Per-game differences of the chunked track viewer (`TrackMapBlockUiComponent`). Everything else
// (world, camera, sky, chunk streaming, fly-to, texture archive picker) is shared.
export interface TrackMapAdapter {
  // Terrain chunk positions, in game coordinates (Y up). One serialized `terrain_chunk_<i>.obj` per item. When not
  // set, positions are read from `terrain_chunks.json`, written by the serializer next to the chunks
  chunkPositions?(data: BlockData): Point3[];
  // For tracks whose block data doesn't carry the road spline: reads chunk positions, spline and loop flag from the
  // files serialized for the viewer. When set, `chunkPositions`, `splinePoints` and `isClosed` are not used
  loadLayout?(serializedPaths: string[]): Promise<TrackLayout>;
  // Road spline for the minimap and the "Spline item" fly-to. Defaults to the chunk positions
  splinePoints?(data: BlockData): TrackSplinePoint[];
  // Whether the last chunk connects to the first one. Defaults to true
  isClosed?(data: BlockData): boolean;
  // Texture archive file kind, shown in the picker ("QFS", "FAM")
  textureArchiveKind?: string;
  // Glob patterns (wildcards in file name only, case-insensitive) of texture archives for this track,
  // most preferred first. Every match is offered in the picker and the first one is loaded
  textureArchivePatterns?(resourceId: string): string[];
  // Terrain textures are written by the track serializer to `textures/<name>.png` next to the chunks, so there
  // is no texture archive picker
  bundledTextures?: boolean;
  // Alpha test of terrain materials, for textures with alpha masks (foliage, fences)
  terrainAlphaTest?: number;
  // Serializer settings patch used when exporting the texture archive
  textureArchiveSettings?: { [key: string]: any };
  // Whether the texture archive provides a spherical skybox texture
  hasSkybox: boolean;
  // Wrapping/orientation of terrain textures. Defaults to repeat in both directions
  setupTerrainTexture?(texture: Texture): void;
  // Extra entities placed on a terrain chunk (e.g. props)
  loadChunkProps?(map: TrackMapWorldEntity, chunkIndex: number): Promise<TrackEntity[]>;
  // Graph of terrain chunks (viewer coordinates), loaded around the camera up to `loadDepth` hops. Defaults to a
  // chain in chunk order, as a road goes
  chunkGraph?(nodes: MapGraphNodeType[]): MapGraph;
  // How many graph hops around the camera are loaded. Defaults to 40
  loadDepth?: number;
  // Minimap shows spline points as dots instead of a road line
  minimapPointsOnly?: boolean;
  // Panels with the data of the selected spline point. When set, `commonFields` lists the fields
  // shown in the "Common" panel instead of the whole track block
  splineDetailPanels?: TrackSplineDetailPanel[];
  commonFields?: string[];
}

function splitPath(resourceId: string): { dir: string; base: string } {
  const slash = Math.max(resourceId.lastIndexOf('/'), resourceId.lastIndexOf('\\'));
  const dir = resourceId.substring(0, slash + 1);
  const fileName = resourceId.substring(slash + 1);
  const dot = fileName.lastIndexOf('.');
  return { dir, base: dot > 0 ? fileName.substring(0, dot) : fileName };
}

// "<dir>/<track>.<ext>" -> "<dir>/<track>0.QFS", then any other QFS in the same folder
function qfsPatterns(resourceId: string): string[] {
  const { dir, base } = splitPath(resourceId);
  return [`${dir}${base}0.QFS`, `${dir}*.QFS`];
}

export const NFS2_TRACK_ADAPTER: TrackMapAdapter = {
  chunkPositions: data => data['block_positions'] || [],
  textureArchiveKind: 'QFS',
  textureArchivePatterns: qfsPatterns,
  hasSkybox: true,
};

export const NFS3_TRACK_ADAPTER: TrackMapAdapter = {
  chunkPositions: data => (data['blocks'] || []).map((b: any) => b.position),
  textureArchiveKind: 'QFS',
  textureArchivePatterns: qfsPatterns,
  hasSkybox: true,
};

// NFS4's FRD track blocks store their position in `blocks_headers[i].position` (a separate array
// from the block bodies in `blocks`), unlike NFS3 where each block carries its own `position` inline.
export const NFS4_TRACK_ADAPTER: TrackMapAdapter = {
  chunkPositions: data => (data['blocks_headers'] || []).map((h: any) => h.position),
  textureArchiveKind: 'QFS',
  textureArchivePatterns: resourceId => {
    // Same convention as the backend's Nfs4FrdMapSerializer: the track's texture archive is named
    // after the .FRD's basename + "0.QFS". A reverse-direction track ("Trn.FRD") doesn't always have
    // its own archive (e.g. GT1, GT2, Park only ship the forward track's "Tr0.QFS", which the
    // reverse FRD's polygons reference directly), so the forward one comes next.
    const { dir, base } = splitPath(resourceId);
    const patterns = [`${dir}${base}0.QFS`];
    if (base.slice(-1).toLowerCase() === 'n') {
      patterns.push(`${dir}${base.slice(0, -1)}0.QFS`);
    }
    return [...patterns, `${dir}*.QFS`];
  },
  hasSkybox: false,
};

// TNFS TRI: 4 road spline points per terrain chunk; props and textures come from a FAM file in
// SIMDATA/{E,G,N}TRACKFM next to SIMDATA/MISC where the TRI lives
export const TNFS_TRACK_ADAPTER: TrackMapAdapter = {
  chunkPositions: data =>
    (data['road_spline'] || [])
      .filter((_: any, i: number) => i % 4 === 0)
      .slice(0, data['num_chunks'])
      .map((p: any) => p.position),
  splinePoints: data =>
    (data['road_spline'] || [])
      .slice(0, (data['num_chunks'] || 0) * 4)
      .map((p: any) => ({ position: p.position, orientation: p.orientation })),
  isClosed: data => data['loop_chunk'] !== 0,
  textureArchiveKind: 'FAM',
  textureArchivePatterns: resourceId => {
    const { dir, base } = splitPath(resourceId);
    const trackName = base.substring(0, 3);
    const simDataDir = /(^|[\/\\])MISC[\/\\]$/i.test(dir) ? dir.substring(0, dir.length - 5) : dir;
    return [
      `${simDataDir}ETRACKFM/${trackName}_001.FAM`,
      `${simDataDir}ETRACKFM/${trackName}_*.FAM`,
      `${simDataDir}GTRACKFM/${trackName}_*.FAM`,
      `${simDataDir}NTRACKFM/${trackName}_*.FAM`,
      `${dir}${trackName}_*.FAM`,
    ];
  },
  textureArchiveSettings: {
    geometry__save_obj: true,
    geometry__save_blend: false,
    geometry__export_to_gg_web_engine: false,
  },
  hasSkybox: true,
  setupTerrainTexture: (texture: Texture) => {
    texture.wrapS = RepeatWrapping;
    texture.wrapT = ClampToEdgeWrapping;
    setupNfs1Texture(texture);
    texture.flipY = true;
  },
  loadChunkProps: loadTnfsChunkProps,
  splineDetailPanels: [
    { title: 'Road spline item', field: 'road_spline', itemsPerEntry: 1 },
    { title: 'AI info (block for 4 spline items)', field: 'ai_info', itemsPerEntry: 4 },
    { title: 'Terrain (block for 4 spline items)', field: 'terrain', itemsPerEntry: 4 },
  ],
  commonFields: [
    'loop_chunk',
    'num_chunks',
    'unk0',
    'unk1',
    'position',
    'unknowns0',
    'chunks_size',
    'rail_tex_id',
    'num_prop_descr',
    'num_props',
    'unk2',
    'unk3',
    'prop_descr',
    'props',
  ],
};

// NFS6 race route (levelNN/aipaths.dat): one chunk per compartment ("compNN.o" listed in drvpath.ini), textures
// come with the chunks
export const NFS6_TRACK_ADAPTER: TrackMapAdapter = {
  splinePoints: data => nfs6Route(data).points,
  isClosed: data => nfs6Route(data).closed,
  bundledTextures: true,
  terrainAlphaTest: 0.5,
  hasSkybox: false,
  setupTerrainTexture: (texture: Texture) => {
    texture.wrapS = RepeatWrapping;
    texture.wrapT = RepeatWrapping;
    texture.colorSpace = 'srgb';
    texture.anisotropy = 8;
  },
};

// Every node is connected to `k` nearest ones, so the camera loads chunks around it in every direction (a city).
// Separate clusters are joined by their closest nodes, so that every node is reachable from the returned root
export function proximityChunkGraph(nodes: MapGraphNodeType[], k: number = 8): MapGraph {
  const graphs = nodes.map(n => new MapGraph(n));
  const distSq = (i: number, j: number) =>
    (nodes[i].position.x - nodes[j].position.x) ** 2 +
    (nodes[i].position.y - nodes[j].position.y) ** 2 +
    (nodes[i].position.z - nodes[j].position.z) ** 2;
  for (let i = 0; i < nodes.length; i++) {
    nodes
      .map((_, j) => ({ j, d: distSq(i, j) }))
      .filter(x => x.j !== i)
      .sort((a, b) => a.d - b.d)
      .slice(0, k)
      .forEach(({ j }) => graphs[i].addAdjacent(graphs[j]));
  }
  if (!graphs.length) {
    return new MapGraph({ path: '', position: { x: 0, y: 0, z: 0 }, loadOptions: {} });
  }
  const connected = new Set(graphs[0].nodes());
  while (connected.size < graphs.length) {
    let best: [number, number, number] = [-1, -1, Infinity];
    for (let i = 0; i < graphs.length; i++) {
      if (!connected.has(graphs[i])) {
        continue;
      }
      for (let j = 0; j < graphs.length; j++) {
        if (!connected.has(graphs[j]) && distSq(i, j) < best[2]) {
          best = [i, j, distSq(i, j)];
        }
      }
    }
    graphs[best[0]].addAdjacent(graphs[best[1]]);
    graphs[best[1]].nodes().forEach(n => connected.add(n));
  }
  return graphs[0];
}

// NFS Underground race bundle (TRACKS/TRACKBnnnn.lzc): one chunk per scenery of the streamed world sections, textures
// come with the chunks. No race route yet: the minimap shows chunk centers
export const NFSU_TRACK_ADAPTER: TrackMapAdapter = {
  isClosed: () => false,
  bundledTextures: true,
  terrainAlphaTest: 0.5,
  hasSkybox: false,
  setupTerrainTexture: (texture: Texture) => {
    texture.wrapS = RepeatWrapping;
    texture.wrapT = RepeatWrapping;
    texture.colorSpace = 'srgb';
    texture.anisotropy = 8;
  },
  chunkGraph: nodes => proximityChunkGraph(nodes),
  loadDepth: 3,
  minimapPointsOnly: true,
};

// NFS5 CRP track ("karT"): the backend splits the meshes into chunks, one per road piece, and writes their
// positions and road headings to `track_layout.json`. Textures come from the FSH file, referenced by the CRP
export const NFS5_TRACK_ADAPTER: TrackMapAdapter = {
  loadLayout: async (serializedPaths: string[]) => {
    const layoutPath = serializedPaths.find(x => x.endsWith('track_layout.json'));
    const layout = layoutPath ? await (await fetch(layoutPath)).json() : { chunks: [], closed: false };
    return {
      chunkPositions: layout.chunks.map((c: any) => c.position),
      splinePoints: layout.chunks.map((c: any) => ({ position: c.position, orientation: c.orientation })),
      isClosed: layout.closed,
    };
  },
  textureArchiveKind: 'FSH',
  textureArchivePatterns: resourceId => {
    const { dir, base } = splitPath(resourceId);
    return [`${dir}${base}.fsh`, `${dir}*.fsh`];
  },
  hasSkybox: false,
};

// Keyed by block class name, as found in `BlockSchema.block_class_mro`
export const TRACK_MAP_ADAPTERS: { [blockClass: string]: TrackMapAdapter } = {
  TriMap: TNFS_TRACK_ADAPTER,
  TrkMap: NFS2_TRACK_ADAPTER,
  FrdMap: NFS3_TRACK_ADAPTER,
  Nfs4FrdMap: NFS4_TRACK_ADAPTER,
  Nfs6AiPaths: NFS6_TRACK_ADAPTER,
  CrpGeometry: NFS5_TRACK_ADAPTER,
  NfsuTrackBundle: NFSU_TRACK_ADAPTER,
};

export function findTrackMapAdapter(blockClassMro: string | undefined): TrackMapAdapter | null {
  for (const className of (blockClassMro || '').split('__')) {
    if (TRACK_MAP_ADAPTERS[className]) {
      return TRACK_MAP_ADAPTERS[className];
    }
  }
  return null;
}
