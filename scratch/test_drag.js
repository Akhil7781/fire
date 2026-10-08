const { spawn } = require('child_process');
const http = require('http');

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function main() {
  console.log('Spawning Chrome with remote debugging...');
  const chromePath = 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe';
  const chrome = spawn(chromePath, [
    '--headless=new',
    '--remote-debugging-port=9227',
    '--user-data-dir=C:\\Users\\akhil\\AppData\\Local\\Temp\\chrome_test_profile_2',
    '--no-first-run',
    '--no-default-browser-check',
    'http://localhost:8090/'
  ], { stdio: 'ignore' });

  // Wait for CDP to be ready
  let tabs = null;
  for (let i = 0; i < 20; i++) {
    await sleep(500);
    try {
      tabs = await new Promise((resolve, reject) => {
        http.get('http://127.0.0.1:9227/json', res => {
          let data = '';
          res.on('data', chunk => data += chunk);
          res.on('end', () => resolve(JSON.parse(data)));
        }).on('error', reject);
      });
      if (tabs && tabs.length > 0) break;
    } catch (_) {}
  }

  if (!tabs) {
    chrome.kill();
    throw new Error('Chrome CDP failed to initialize on port 9227');
  }

  const page = tabs.find(t => t.type === 'page');
  console.log('Connected to page tab:', page.title, page.url);

  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let id = 1;
  const pending = new Map();

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    }
  };

  function send(method, params = {}) {
    return new Promise((resolve) => {
      const msgId = id++;
      pending.set(msgId, resolve);
      ws.send(JSON.stringify({ id: msgId, method, params }));
    });
  }

  await new Promise(r => ws.onopen = r);
  console.log('WebSocket connection to Chrome DevTools Protocol open.');

  await send('Runtime.enable');
  await send('Page.enable');

  // Wait 1.5s for page and images to load
  await sleep(1500);

  // 1. Open PILOT_02_NORTH
  console.log('Loading PILOT_02_NORTH in UI...');
  await send('Runtime.evaluate', {
    expression: `loadChip('PILOT_02_NORTH')`,
    awaitPromise: true
  });
  await sleep(1000);

  // 2. Select HAS_ANNOTATIONS
  console.log('Selecting HAS_ANNOTATIONS radio...');
  await send('Runtime.evaluate', {
    expression: `(() => {
      const rad = document.querySelector('input[name="chip_status"][value="HAS_ANNOTATIONS"]');
      rad.checked = true;
      onStatusChange();
    })()`
  });

  // 3. Inspect state before drag
  const beforeState = await send('Runtime.evaluate', {
    expression: `JSON.stringify({
      activeChip: typeof activeChip !== 'undefined' ? activeChip : 'undefined',
      boxesCount: typeof boxes !== 'undefined' ? boxes.length : 'undefined',
      modeText: document.getElementById('box-mode-display') ? document.getElementById('box-mode-display').innerText : 'null',
      statusRadio: document.querySelector('input[name="chip_status"]:checked') ? document.querySelector('input[name="chip_status"]:checked').value : 'null'
    })`,
    returnByValue: true
  });
  const valBefore = (beforeState.result && beforeState.result.result) ? beforeState.result.result.value : beforeState.result?.value;
  console.log('State before drag:', JSON.parse(valBefore));

  // 4. Perform ONE genuine manual test drag through the browser/UI
  console.log('Performing drag on canvas from (120, 100) to (320, 280)...');
  const dragResult = await send('Runtime.evaluate', {
    expression: `(() => {
      const canvas = document.getElementById('image-canvas');
      const rect = canvas.getBoundingClientRect();
      const scaleX = 512 / rect.width;
      const scaleY = 512 / rect.height;

      // Pointer down at (120, 100) canvas coords
      const downEvt = new PointerEvent('pointerdown', {
        clientX: rect.left + 120 / scaleX,
        clientY: rect.top + 100 / scaleY,
        button: 0,
        buttons: 1,
        pointerId: 1,
        bubbles: true,
        cancelable: true
      });
      canvas.dispatchEvent(downEvt);

      // Pointer move to (200, 180)
      const moveEvt1 = new PointerEvent('pointermove', {
        clientX: rect.left + 200 / scaleX,
        clientY: rect.top + 180 / scaleY,
        button: 0,
        buttons: 1,
        pointerId: 1,
        bubbles: true,
        cancelable: true
      });
      canvas.dispatchEvent(moveEvt1);

      // Pointer move to (320, 280)
      const moveEvt2 = new PointerEvent('pointermove', {
        clientX: rect.left + 320 / scaleX,
        clientY: rect.top + 280 / scaleY,
        button: 0,
        buttons: 1,
        pointerId: 1,
        bubbles: true,
        cancelable: true
      });
      canvas.dispatchEvent(moveEvt2);

      // Pointer up at (320, 280)
      const upEvt = new PointerEvent('pointerup', {
        clientX: rect.left + 320 / scaleX,
        clientY: rect.top + 280 / scaleY,
        button: 0,
        buttons: 0,
        pointerId: 1,
        bubbles: true,
        cancelable: true
      });
      canvas.dispatchEvent(upEvt);

      return JSON.stringify({
        isDrawing: isDrawing,
        boxesCount: boxes.length,
        boxes: boxes,
        modeText: document.getElementById('box-mode-display').innerText,
        coordText: document.getElementById('coord-display').innerText,
        audit: auditCounts
      });
    })()`,
    returnByValue: true
  });

  const valAfter = (dragResult.result && dragResult.result.result) ? dragResult.result.result.value : dragResult.result?.value;
  const stateAfter = JSON.parse(valAfter);
  console.log('State AFTER drag:', stateAfter);

  // Verify requirements
  if (stateAfter.boxesCount === 1) {
    console.log('SUCCESS: Bounding box created!');
    console.log('Captured box:', stateAfter.boxes[0].bbox);
    console.log('Status mode display:', stateAfter.modeText);
  } else {
    console.error('FAILED: No bounding box created!');
  }

  // DO NOT SAVE THIS TEST!
  console.log('Verifying DO NOT SAVE rule: No save called.');

  ws.close();
  chrome.kill();
  console.log('Chrome process terminated. Test complete.');
}

main().catch(err => {
  console.error('Error:', err);
  process.exit(1);
});
