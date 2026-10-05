import { BlockData } from '../../types';
import type { TrackSplinePoint } from './track-map-adapters';

export interface Nfs6Route {
  points: TrackSplinePoint[];
  closed: boolean;
}

interface GraphEdge {
  to: string;
  path: number;
  reversed: boolean;
}

const routes = new WeakMap<BlockData, Nfs6Route>();

function nodeKey(p: { x: number; y: number; z: number }): string {
  return `${p.x.toFixed(2)},${p.y.toFixed(2)},${p.z.toFixed(2)}`;
}

// The main race route of NFS6 AI path graph (aipaths.dat road paths): paths sharing end positions are connected,
// main road paths (type 1) weigh much more than alternative roads and shortcuts, and a closed loop is preferred
// to an open route of similar length. Found by exhaustive search, the graphs are small (up to ~25 paths)
export function nfs6Route(data: BlockData): Nfs6Route {
  let route = routes.get(data);
  if (!route) {
    route = findRoute((data['road_paths'] || {})['paths'] || []);
    routes.set(data, route);
  }
  return route;
}

function findRoute(paths: any[]): Nfs6Route {
  const edges = new Map<string, GraphEdge[]>();
  const addEdge = (from: string, edge: GraphEdge) => edges.set(from, [...(edges.get(from) || []), edge]);
  paths.forEach((path, i) => {
    if (!path.points?.length) {
      return;
    }
    const start = nodeKey(path.points[0].position);
    const end = nodeKey(path.points[path.points.length - 1].position);
    addEdge(start, { to: end, path: i, reversed: false });
    addEdge(end, { to: start, path: i, reversed: true });
  });
  const weight = (i: number) => paths[i].points.length * (paths[i].path_type === 1 ? 1 : 0.1);

  let best: { score: number; edges: GraphEdge[]; closed: boolean } = { score: 0, edges: [], closed: false };
  let budget = 200000;
  const usedPaths = new Set<number>();
  const visited = new Set<string>();
  const route: GraphEdge[] = [];
  const search = (start: string, node: string, score: number) => {
    if (--budget < 0) {
      return;
    }
    for (const edge of edges.get(node) || []) {
      if (usedPaths.has(edge.path)) {
        continue;
      }
      const newScore = score + weight(edge.path);
      if (edge.to === start) {
        if (newScore * 1.25 > best.score) {
          best = { score: newScore * 1.25, edges: [...route, edge], closed: true };
        }
        continue;
      }
      if (visited.has(edge.to)) {
        continue;
      }
      if (newScore > best.score) {
        best = { score: newScore, edges: [...route, edge], closed: false };
      }
      usedPaths.add(edge.path);
      visited.add(edge.to);
      route.push(edge);
      search(start, edge.to, newScore);
      route.pop();
      visited.delete(edge.to);
      usedPaths.delete(edge.path);
    }
  };
  for (const start of edges.keys()) {
    visited.add(start);
    search(start, start, 0);
    visited.delete(start);
  }

  const positions: { x: number; y: number; z: number }[] = [];
  for (const edge of best.edges) {
    const points = paths[edge.path].points.map((p: any) => p.position);
    if (edge.reversed) {
      points.reverse();
    }
    positions.push(...(positions.length ? points.slice(1) : points));
  }
  if (best.closed) {
    positions.pop();
  }
  // heading: 0 is +Z, growing towards +X
  const points = positions.map((position, i) => {
    const next = positions[(i + 1) % positions.length];
    const prev = positions[Math.max(i - 1, 0)];
    const [from, to] = i + 1 < positions.length || best.closed ? [position, next] : [prev, position];
    return { position, orientation: Math.atan2(to.x - from.x, to.z - from.z) };
  });
  return { points, closed: best.closed };
}
