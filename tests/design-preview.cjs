// Browser-local visual preview of the actual sidebar; no deployed changes or port actions.
const {chromium}=require('/home/mantiz010/kate2.0/node_modules/playwright');const fs=require('fs'),path=require('path'),assert=require('node:assert/strict');
(async()=>{const b=await chromium.launch({headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});try{
 const token=JSON.parse(fs.readFileSync('/home/mantiz010/.config/et-tools/secrets.json')).ha_token,posts=[];
 const p=await b.newPage({viewport:{width:1400,height:940},reducedMotion:'reduce'});
 p.on('websocket',w=>w.on('framesent',({payload})=>{try{const x=JSON.parse(payload);if(x.type==='call_service')posts.push('websocket service');}catch{}}));
 p.on('request',r=>{if(r.url().includes('/api/serial_reader')&&r.method()!=='GET')posts.push(r.method());});
 await p.addInitScript(t=>localStorage.setItem('hassTokens',JSON.stringify({hassUrl:location.origin,access_token:t,token_type:'Bearer',expires_in:31536000,expires:Date.now()+31536000000,refresh_token:''})),token);
 if(!process.argv.includes('--deployed'))await p.route('**/local/serial_ports.html*',r=>r.fulfill({contentType:'text/html',body:fs.readFileSync(path.resolve(__dirname,'../serial_ports.html'))}));
 fs.mkdirSync('/tmp/serial-reader-design',{recursive:true});
 for(const [width,height] of [[1400,940],[700,1000],[410,800]]){
  await p.setViewportSize({width,height});await p.goto('http://172.168.1.8:8123/serial-reader');const frame=p.locator('hui-iframe-card iframe').contentFrame();await frame.locator('#port-dropdown option').filter({hasText:'ESP-NOW Receiver'}).waitFor({state:'attached'});await frame.locator('#port-dropdown').selectOption('/dev/serial/by-id/espnow-receiver');
  const sizes=await frame.locator('body').evaluate(e=>{const c=document.querySelector('.console-panel'),log=document.querySelector('.terminal');return {scroll:document.documentElement.scrollWidth,w:innerWidth,consoleHeight:c.getBoundingClientRect().height,logHeight:log.getBoundingClientRect().height,appBottom:document.querySelector('.app').getBoundingClientRect().bottom,h:innerHeight,send:document.querySelector('#send-button').disabled,disconnect:document.querySelector('#disconnect-button').disabled,opacity:getComputedStyle(document.querySelector('#disconnect-button')).opacity};});
  assert(sizes.scroll<=sizes.w,'Horizontal overflow '+JSON.stringify(sizes));assert(sizes.logHeight>=80,'Terminal is clipped '+JSON.stringify(sizes));assert(sizes.appBottom<=sizes.h+1,'App extends beyond view '+JSON.stringify(sizes));assert(sizes.send&&sizes.disconnect);assert(Number(sizes.opacity)<.6);
  await frame.getByRole('button',{name:'Pause Display',exact:true}).click();await frame.getByRole('button',{name:'Resume Display',exact:true}).waitFor();await frame.getByRole('button',{name:'Resume Display',exact:true}).click();
  await p.screenshot({path:`/tmp/serial-reader-design/${process.argv.includes('--deployed')?'live':'preview'}-${width}.png`});console.log(width,height,sizes);
  if (width===1400) {
   await p.evaluate(()=>{
    const host=document.querySelector('home-assistant');
    host.hass={...host.hass,themes:{...host.hass.themes,darkMode:true}};
    const map={'--primary-background-color':'#101820','--ha-card-background':'#1b2733','--primary-text-color':'#e5edf5','--secondary-text-color':'#a1b3c3','--divider-color':'#334454'};
    for(const [k,v] of Object.entries(map))host.style.setProperty(k,v);
   });
   const theme=await frame.locator('html').evaluate(()=>{syncTheme();return {mode:document.documentElement.dataset.theme,background:getComputedStyle(document.querySelector('.connection-panel')).backgroundColor};});
   assert.equal(theme.mode,'dark');assert.equal(theme.background,'rgb(27, 39, 51)');
   await p.screenshot({path:`/tmp/serial-reader-design/${process.argv.includes('--deployed')?'live':'preview'}-dark.png`});
  }

 }
 assert.deepEqual(posts,[]);console.log('PASS: actual sidebar preview, desktop/tablet/phone layouts, visible console, clear disabled states, pause only and no serial actions.');
}finally{await b.close();}})().catch(e=>{console.error(e);process.exitCode=1});
