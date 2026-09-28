import time, asyncio
import urllib.request
import json
import logging
from models.registry import get_model_name

logger = logging.getLogger(__name__)

async def ensure_model_loaded(model_name: str, task_id: str):
    logger.info(f"[{task_id}] Loading model {model_name}...")
    # Emulate the vram_manager local call
    try:
        req = urllib.request.Request("http://localhost:11434/api/generate", 
            data=json.dumps({"model": model_name, "keep_alive": "5m"}).encode('utf-8'),
            headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            pass
    except Exception as e:
        logger.error(f"Failed to load {model_name}: {e}")

async def test():
    print('Testing model swap cold-start times...')
    
    start = time.time()
    await ensure_model_loaded('qwen2.5:3b-instruct', 'test-1')
    t1 = time.time() - start
    print(f'Time to load reasoning model: {t1:.2f}s')
    
    # unload reasoning model to force swap
    req = urllib.request.Request("http://localhost:11434/api/generate", 
        data=json.dumps({"model": "qwen2.5:3b-instruct", "keep_alive": 0}).encode('utf-8'),
        headers={'Content-Type': 'application/json'})
    urllib.request.urlopen(req)
    
    start = time.time()
    await ensure_model_loaded('qwen2-vl:2b', 'test-2')
    t2 = time.time() - start
    print(f'Time to swap to vision model: {t2:.2f}s')
    
    print('Done.')

asyncio.run(test())
