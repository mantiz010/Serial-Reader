// Read-only regression check for the actual HA sidebar, never Start or Send.
const {chromium}=require('/home/mantiz010/kate2.0/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('node:assert/strict'),crypto=require('crypto');
(async()=>{
 const token=JSON.parse(fs.readFileSync('/home/mantiz010/.config/et-tools/secrets.json')).ha_token;
 const digest=crypto.createHash('sha256').update(fs.readFileSync(path.resolve(__dirname,'../serial_ports.html'))).digest('hex').slice(0,12);
 const b=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
 try{
  const p=await b.newPage({viewport:{width:1200,height:900}}),mutations=[];
  p.on('request',r=>{if(r.url().includes('/api/serial_reader')&&r.method()!=='GET')mutations.push(r.method());});
  await p.addInitScript(t=>localStorage.setItem('hassTokens',JSON.stringify({hassUrl:location.origin,access_token:t,token_type:'Bearer',expires_in:31536000,expires:Date.now()+31536000000,refresh_token:''})),token);
  await p.goto('http://172.168.1.8:8123/serial-reader');
  const iframe=p.locator('hui-iframe-card iframe');await iframe.waitFor();
  assert.equal(await iframe.getAttribute('src'),'/local/serial_ports.html?v='+digest);
  const frame=iframe.contentFrame();await frame.locator('#port-dropdown option').filter({hasText:'ESP-NOW Wi-Fi Master'}).waitFor({state:'attached'});
  const options=await frame.locator('#port-dropdown option').evaluateAll(es=>es.map(x=>({label:x.textContent,value:x.value})));
  assert(options.some(x=>x.label==='ESP-NOW Receiver — /dev/ttyUSB3'&&x.value==='/dev/serial/by-id/espnow-receiver'));
  assert(options.some(x=>x.label==='ESP-NOW Wi-Fi Master — /dev/ttyUSB4'&&x.value==='/dev/serial/by-id/espnow-wifi-master'));
  assert(!options.some(x=>x.value==='/dev/ttyUSB3'||x.value==='/dev/ttyUSB4'),'No duplicate raw entries for named boards');
  assert.match(await frame.locator('#reader-version').innerText(),/Backend 1\.1\.0/);
  await frame.locator('#port-dropdown').selectOption('/dev/serial/by-id/espnow-receiver');
  assert.match(await frame.locator('#device-detail').innerText(),/ESP-NOW Receiver/);
  fs.mkdirSync('/tmp/serial-reader-proof',{recursive:true});await p.screenshot({path:'/tmp/serial-reader-proof/sidebar.png'});
  assert.deepEqual(mutations,[]);console.log(JSON.stringify({actualSidebarPassed:true,iframeVersion:digest,namedDeviceChoices:options.filter(x=>x.label.startsWith('ESP-NOW')),noDuplicateRawPorts:true,noSerialActions:true}));
 }finally{await b.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
