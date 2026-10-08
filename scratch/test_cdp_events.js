const http = require('http');

async function main() {
  const jsonResp = await new Promise((resolve, reject) => {
    http.get('http://127.0.0.1:9225/json', res => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(JSON.parse(data)));
    }).on('error', reject);
  });

  const page = jsonResp.find(t => t.type === 'page');
  console.log('Connecting to page:', page.title, page.webSocketDebuggerUrl);

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
  console.log('WebSocket connected.');

  // Enable Runtime
  await send('Runtime.enable');

  // Evaluate current state of variables in page
  const evalRes1 = await send('Runtime.evaluate', {
    expression: `JSON.stringify({
      activeChip: activeChip,
      boxesCount: boxes.length,
      isDrawing: isDrawing,
      canvasRect: document.getElementById('image-canvas').getBoundingClientRect()
    })`,
    returnByValue: true
  });
  console.log('Page state before drag:', evalRes1.result.value);

  // Switch to PILOT_02_NORTH and select HAS_ANNOTATIONS
  await send('Runtime.evaluate', {
    expression: `(async () => {
      await loadChip('PILOT_02_NORTH');
      document.querySelector('input[name="chip_status"][value="HAS_ANNOTATIONS"]').checked = true;
      onStatusChange();
    })()`,
    awaitPromise: true
  });

  // Now simulate a drag using Synthetic Mouse Events via Runtime evaluate
  const dragResult = await send('Runtime.evaluate', {
    expression: `(() => {
      const v = document.getElementById('canvas-viewport');
      const c = document.getElementById('image-canvas');
      const rect = c.getBoundingClientRect();
      
      const logs = [];
      const origRedraw = redraw;
      let redrawCalls = 0;
      window.redraw = function() { redrawCalls++; return origRedraw.apply(this, arguments); };

      // Dispatch mousedown
      const downEvt = new MouseEvent('mousedown', {
        clientX: rect.left + 100,
        clientY: rect.top + 100,
        button: 0,
        bubbles: true,
        cancelable: true
      });
      c.dispatchEvent(downEvt);
      logs.push({ step: 'after_down', isDrawing: isDrawing, startX: startX, startY: startY });

      // Dispatch mousemove
      const moveEvt = new MouseEvent('mousemove', {
        clientX: rect.left + 250,
        clientY: rect.top + 250,
        button: 0,
        bubbles: true,
        cancelable: true
      });
      c.dispatchEvent(moveEvt);
      logs.push({ step: 'after_move', isDrawing: isDrawing, currentX: currentX, currentY: currentY, redrawCalls: redrawCalls });

      // Dispatch mouseup on window
      const upEvt = new MouseEvent('mouseup', {
        clientX: rect.left + 250,
        clientY: rect.top + 250,
        button: 0,
        bubbles: true,
        cancelable: true
      });
      window.dispatchEvent(upEvt);
      logs.push({ step: 'after_up', isDrawing: isDrawing, boxesCount: boxes.length, boxes: boxes });

      return JSON.stringify(logs);
    })()`,
    returnByValue: true
  });

  console.log('Synthetic drag logs on image-canvas:', JSON.parse(dragResult.result.value));

  // Now test actual Input.dispatchMouseEvent CDP events (real browser input pipeline!)
  console.log('Testing Input.dispatchMouseEvent CDP events...');
  
  // Get canvas position
  const posRes = await send('Runtime.evaluate', {
    expression: `(() => {
      const c = document.getElementById('image-canvas');
      const r = c.getBoundingClientRect();
      boxes = []; // reset test boxes
      return { x: r.left, y: r.top, width: r.width, height: r.height };
    })()`,
    returnByValue: true
  });
  const rect = posRes.result.value;
  console.log('Canvas client rect:', rect);

  // Mouse move to start
  await send('Input.dispatchMouseEvent', {
    type: 'mouseMoved',
    x: rect.x + 50,
    y: rect.y + 50
  });

  // Mouse down
  await send('Input.dispatchMouseEvent', {
    type: 'mousePressed',
    button: 'left',
    buttons: 1,
    clickCount: 1,
    x: rect.x + 50,
    y: rect.y + 50
  });

  // Mouse drag moves
  for (let i = 1; i <= 5; i++) {
    await send('Input.dispatchMouseEvent', {
      type: 'mouseMoved',
      button: 'left',
      buttons: 1,
      x: rect.x + 50 + i * 30,
      y: rect.y + 50 + i * 30
    });
  }

  // Mouse up
  await send('Input.dispatchMouseEvent', {
    type: 'mouseReleased',
    button: 'left',
    buttons: 0,
    clickCount: 1,
    x: rect.x + 200,
    y: rect.y + 200
  });

  // Check state after real CDP mouse input
  const cdpCheck = await send('Runtime.evaluate', {
    expression: `JSON.stringify({
      isDrawing: isDrawing,
      boxesCount: boxes.length,
      boxes: boxes,
      boxModeText: document.getElementById('coord-display').innerText
    })`,
    returnByValue: true
  });
  console.log('Result after real CDP drag:', JSON.parse(cdpCheck.result.value));

  ws.close();
}

main().catch(err => console.error(err));
