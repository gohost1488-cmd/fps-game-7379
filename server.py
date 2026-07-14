"""AHVE FPS Server — fps-game-7379."""
import asyncio, json, time, math, random, uuid
from aiohttp import web
import aiohttp

players = {}
matches = {}
queue = []

async def index(request):
    return web.FileResponse('index.html')

async def ws_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    pid = str(uuid.uuid4())[:8]
    players[pid] = {'id': pid, 'x': random.uniform(0, 600), 'y': random.uniform(0, 400), 'hp': 100, 'kills': 0, 'color': random.choice(['red','blue','green','orange','purple'])}
    await ws.send_json({'type': 'init', 'player_id': pid, 'players': list(players.values())})
    
    for other_id, other in players.items():
        if other_id != pid:
            for ws2 in request.app['websockets'].get(other_id, []):
                await ws2.send_json({'type': 'player_joined', 'player': players[pid]})
    
    request.app['websockets'].setdefault(pid, []).append(ws)
    
    try:
        async for msg in ws:
            data = json.loads(msg.data)
            p = players[pid]
            if data.get('move'):
                dx, dy = data['move']['x'], data['move']['y']
                p['x'] = max(10, min(790, p['x'] + dx * 5))
                p['y'] = max(10, min(590, p['y'] + dy * 5))
            
            if data.get('shoot'):
                mx, my = data['shoot']['x'], data['shoot']['y']
                for oid, o in players.items():
                    if oid != pid and abs(o['x'] - mx) < 20 and abs(o['y'] - my) < 20:
                        o['hp'] -= 25
                        if o['hp'] <= 0:
                            o['hp'] = 100
                            o['x'] = random.uniform(0, 600)
                            o['y'] = random.uniform(0, 400)
                            p['kills'] += 1
                            await ws.send_json({'type': 'kill', 'victim': oid, 'kills': p['kills']})
                            for ws2 in request.app['websockets'].get(oid, []):
                                await ws2.send_json({'type': 'respawn', 'x': o['x'], 'y': o['y']})
                        break
            
            await ws.send_json({'type': 'state', 'players': list(players.values())})
    finally:
        request.app['websockets'][pid].remove(ws)
        del players[pid]
        for ws2_list in request.app['websockets'].values():
            for ws2 in ws2_list:
                await ws2.send_json({'type': 'player_left', 'player_id': pid})
    
    return ws

app = web.Application()
app['websockets'] = {}
app.router.add_get('/', index)
app.router.add_get('/ws', ws_handler)

if __name__ == '__main__':
    web.run_app(app, port=5000)
