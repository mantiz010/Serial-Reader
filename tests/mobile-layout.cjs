// Synthetic API only: no USB device is opened, closed or sent a command.
const {chromium}=require('/home/mantiz010/kate2.0/node_modules/playwright');
const fs=require('fs'),path=require('path'),http=require('http'),assert=require('node:assert/strict');
const html=fs.readFileSync(path.resolve(__dirname,'../serial_ports.html'));
const port='/dev/serial/by-id/bresser-weather-receiver';
let posts=0,failed=false,polls=0,sequence=0;
const device={device:'/dev/ttyACM1',name:'Bresser 6-in-1 Weather Receiver',preferred_path:port,aliases:[port]};
const server=http.createServer((req,res)=>{
  if(req.url==='/api/serial_reader'){
    if(req.method!=='GET'){posts++;res.writeHead(500);return res.end();}
    polls++;
    if(failed){res.writeHead(503);return res.end();}
    res.setHeader('Content-Type','application/json');
    const lines=Array.from({length:80},(_,i)=>`[2026-11-04 18:30:48][${port}] Weather sample ${i+sequence}`);
    return res.end(JSON.stringify({version:'1.2.0',capabilities:['connection_actions'],port_details:[{...device,status:'connected'}],active_ports:[port],active_port_details:[{...device,path:port,baud_rate:115200}],serial_data:lines}));
  }
  if(req.url.endsWith('.png')){res.writeHead(204);return res.end();}
  res.setHeader('Content-Type','text/html');res.end(html);
});
(async()=>{
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const browser=await chromium.launch({headless:true});
  try{
    const page=await browser.newPage({viewport:{width:360,height:584}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://127.0.0.1:'+server.address().port);
    await page.locator('#connection-state').filter({hasText:'Connected'}).waitFor();
    assert.equal(await page.locator('#connection-options').evaluate(e=>e.open),false);
    for(const selector of ['#port-dropdown','#follow-button','#pause-button','#command-input','#send-button']){
      const box=await page.locator(selector).boundingBox();assert(box.height>=44,selector+' needs a touch target');
    }
    assert.equal(await page.locator('#command-input').evaluate(e=>getComputedStyle(e).fontSize),'16px');
    assert(!(await page.locator('#serial-data').innerText()).includes('/dev/serial/'),'Phone log repeats long USB paths');
    await page.locator('#connection-options summary').click();
    assert(await page.locator('#baud-dropdown').isVisible());
    await page.locator('#connection-options summary').click();
    await page.waitForTimeout(60);
    await page.locator('#serial-data').evaluate(e=>e.scrollTop=0);
    await page.waitForFunction(()=>document.getElementById('follow-button').getAttribute('aria-pressed')==='false');
    sequence++;
    await page.evaluate(()=>refresh(true));
    assert((await page.locator('#serial-data').evaluate(e=>e.scrollTop))<2,'Refresh stole the reading position');
    await page.getByRole('button',{name:'Follow live output'}).click();
    await page.waitForTimeout(50);
    const gap=await page.locator('#serial-data').evaluate(e=>e.scrollHeight-e.scrollTop-e.clientHeight);
    assert(gap<2,'Follow live did not return to the latest line');
    await page.getByRole('button',{name:'Pause Display',exact:true}).click();
    const paused=await page.locator('#serial-data').innerText();sequence++;
    await page.evaluate(()=>refresh(true));
    assert.equal(await page.locator('#serial-data').innerText(),paused);
    await page.getByRole('button',{name:'Resume Display',exact:true}).click();
    assert.notEqual(await page.locator('#serial-data').innerText(),paused);
    failed=true;await page.evaluate(()=>refresh(true));
    assert.match(await page.locator('#health-label').innerText(),/Reconnecting/);
    failed=false;await page.evaluate(()=>refresh(true));
    assert.equal(await page.locator('#health-label').innerText(),'Online');
    assert.equal(await page.locator('#viewer-status').innerText(),'');
    await page.evaluate(()=>{Object.defineProperty(document,'hidden',{value:true,configurable:true});document.dispatchEvent(new Event('visibilitychange'));});
    assert.equal(await page.evaluate(()=>window.serialRefresh),null);
    await page.evaluate(()=>{Object.defineProperty(document,'hidden',{value:false,configurable:true});document.dispatchEvent(new Event('visibilitychange'));});
    await page.waitForFunction(()=>window.serialRefresh!==null);
    await page.setViewportSize({width:390,height:340});
    await page.locator('#command-input').focus();
    await page.waitForFunction(()=>document.querySelector('.app').classList.contains('keyboard-open'));
    const keyboard=await page.locator('.command-bar').boundingBox();assert(keyboard.y+keyboard.height<=340,'Keyboard-sized viewport hides Send');
    assert((await page.locator('.terminal').boundingBox()).height>=100,'Keyboard-sized viewport loses console');
    await page.locator('#command-input').blur();
    await page.setViewportSize({width:1200,height:900});
    await page.waitForFunction(()=>document.getElementById('connection-options').open);
    await page.evaluate(()=>refresh(true));
    assert((await page.locator('#serial-data').innerText()).includes('/dev/serial/'),'Desktop lost full log labels');
    assert.deepEqual(errors,[]);assert.equal(posts,0);assert(polls>5);
    console.log('PASS: mobile touch targets, connection drawer, compact logs, manual scroll/follow, pause, API recovery, foreground refresh, keyboard-sized viewport, desktop labels and zero serial actions.');
  }finally{await browser.close();await new Promise(r=>server.close(r));}
})().catch(e=>{console.error(e);server.close();process.exitCode=1;});
