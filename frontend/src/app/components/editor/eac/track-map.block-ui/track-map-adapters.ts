import { Point3 } from '@gg-web-engine/core';
import { BlockData } from '../../types';

// Per-game differences of the chunked track viewer (`TrackMapBlockUiComponent`). Everything else
// (world, camera, sky, chunk streaming, fly-to) is shared.
export interface TrackMapAdapter {
  // Track block (= terrain chunk) positions, in game coordinates (Y up)
  blockPositions(data: BlockData): Point3[];
  // QFS texture archive guesses for a track resource id, tried in order until one loads
  qfsCandidates(resourceId: string): string[];
  // Whether the QFS archive provides a spherical skybox texture
  hasSkybox: boolean;
}

// "<track>.<ext>" -> "<track>0.QFS"
function sameNameQfs(resourceId: string, extension: string): string {
  return resourceId.substring(0, resourceId.indexOf(extension)) + '0.QFS';
}

export const NFS2_TRACK_ADAPTER: TrackMapAdapter = {
  blockPositions: data => data['block_positions'] || [],
  qfsCandidates: resourceId => [sameNameQfs(resourceId, '.TRK')],
  hasSkybox: true,
};

export const NFS3_TRACK_ADAPTER: TrackMapAdapter = {
  blockPositions: data => (data['blocks'] || []).map((b: any) => b.position),
  qfsCandidates: resourceId => [sameNameQfs(resourceId, '.FRD')],
  hasSkybox: true,
};

// NFS4's FRD track blocks store their position in `blocks_headers[i].position` (a separate array
// from the block bodies in `blocks`), unlike NFS3 where each block carries its own `position` inline.
export const NFS4_TRACK_ADAPTER: TrackMapAdapter = {
  blockPositions: data => (data['blocks_headers'] || []).map((h: any) => h.position),
  qfsCandidates: resourceId => {
    // Same primary convention as the backend's Nfs4FrdMapSerializer: the track's texture archive
    // is named after the .FRD's own basename with the extension replaced by "0.QFS". A
    // reverse-direction track ("Trn.FRD") doesn't always have its own archive though - some
    // tracks (e.g. GT1, GT2, Park) only ship the forward track's "Tr0.QFS", which the reverse
    // FRD's polygons reference directly - so fall back to that (basename with a trailing "n"
    // stripped) if the primary guess turns out not to exist.
    const base = resourceId.substring(0, resourceId.length - 4);
    const candidates = [base + '0.QFS'];
    const segments = base.split('/');
    const filenamePart = segments[segments.length - 1];
    if (filenamePart.slice(-1).toLowerCase() === 'n') {
      segments[segments.length - 1] = filenamePart.slice(0, -1);
      candidates.push(segments.join('/') + '0.QFS');
    }
    return candidates;
  },
  hasSkybox: false,
};

// Keyed by block class name, as found in `BlockSchema.block_class_mro`
export const TRACK_MAP_ADAPTERS: { [blockClass: string]: TrackMapAdapter } = {
  TrkMap: NFS2_TRACK_ADAPTER,
  FrdMap: NFS3_TRACK_ADAPTER,
  Nfs4FrdMap: NFS4_TRACK_ADAPTER,
};

export function findTrackMapAdapter(blockClassMro: string | undefined): TrackMapAdapter | null {
  for (const className of (blockClassMro || '').split('__')) {
    if (TRACK_MAP_ADAPTERS[className]) {
      return TRACK_MAP_ADAPTERS[className];
    }
  }
  return null;
}
