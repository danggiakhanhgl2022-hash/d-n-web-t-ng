"""Inventory actual GLB nodes and animation targets without modifying assets."""
import json
import struct
from pathlib import Path

root = Path(__file__).resolve().parents[1]
public = root / 'frontend/public'
scenes = json.loads((public / 'renaissance/3d/scenes.json').read_text(encoding='utf-8'))
result = {}
for scene in scenes:
    assets = []
    for url in scene['assets']:
        if not url.endswith('.glb'):
            assets.append({'file': url.rsplit('/', 1)[-1], 'kind': 'image or video plane'})
            continue
        path = public / url.lstrip('/')
        raw = path.read_bytes()
        data = json.loads(raw[20:20 + struct.unpack_from('<I', raw, 12)[0]])
        nodes = data.get('nodes', [])
        parents = {}
        for index, node in enumerate(nodes):
            for child in node.get('children', []):
                parents[child] = index
        def lineage(index):
            chain = []
            while index in parents:
                index = parents[index]
                chain.append(nodes[index].get('name', f'node-{index}'))
            return list(reversed(chain))
        targets = {}
        clips = []
        for animation in data.get('animations', []):
            name = animation.get('name', 'unnamed')
            clips.append({'name': name, 'channels': len(animation.get('channels', []))})
            for channel in animation.get('channels', []):
                index = channel.get('target', {}).get('node')
                if index is not None:
                    targets.setdefault(index, set()).add(name)
        meshes = [{'index': i, 'name': node.get('name', f'node-{i}'),
                   'parents': lineage(i), 'skinned': 'skin' in node,
                   'clips_targeting_node': sorted(targets.get(i, set()))}
                  for i, node in enumerate(nodes) if 'mesh' in node]
        assets.append({'file': path.name, 'kind': 'glb', 'node_count': len(nodes),
                       'meshes': meshes, 'clips': clips})
    result[scene['id']] = assets
out = root / 'runtime/verification/cinema-parts-inventory.json'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
for name, assets in result.items():
    print(name, ', '.join(f"{a['file']}: {len(a.get('meshes', []))} meshes, {len(a.get('clips', []))} clips" for a in assets))
print('Inventory: runtime/verification/cinema-parts-inventory.json')
