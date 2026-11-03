const {chromium}=require('/home/mantiz010/kate2.0/node_modules/playwright');
const fs=require('fs'),http=require('http'),assert=require('node:assert/strict'),path=require('path');
const root=path.resolve(__dirname,'..');let posts=[],fail=false,active={'/dev/ttyUSB8':115200};
const devices=[{device:'/dev/ttyUSB9',name:'ESP-NOW Receiver',preferred_path:'/dev/serial/by-id/espnow-receiver',aliases:['/dev/serial/by-id/espnow-receiver']},{device:'/dev/ttyUSB8',name:'ESP-NOW Wi-Fi Master',preferred_path:'/dev/serial/by-id/espnow-wifi-master',aliases:['/dev/serial/by-id/espnow-wifi-master']},{device:'/dev/ttyACM9',name:'SMS Text Gateway',preferred_path:'/dev/serial/by-id/sms-text-gateway',aliases:['/dev/serial/by-id/sms-text-gateway']},{device:'/dev/ttyACM8',name:'Bresser 6-in-1 Weather Receiver',preferred_path:'/dev/serial/by-id/bresser-weather-receiver',aliases:['/dev/serial/by-id/bresser-weather-receiver']}];
const find=p=>devices.find(d=>d.device===p||d.preferred_path===p);
const server=http.createServer((req,res)=>{
 res.setHeader('Content-Type','application/json');
 if(req.url==='/api/serial_reader'){
  if(req.method==='GET')return res.end(JSON.stringify({version:'1.2.0',capabilities:['connection_actions'],available_ports:devices.map(d=>d.device),port_details:devices.map(d=>({...d,status:active[d.device]?'connected':'disconnected'})),active_ports:Object.keys(active),active_port_details:Object.entries(active).map(([p,baud])=>({...find(p),path:p,baud_rate:baud})),serial_data:[]}));
  let data='';req.on('data',x=>data+=x);req.on('end',()=>{const body=JSON.parse(data);posts.push(body);if(fail)return res.end(JSON.stringify({status:'error',message:'Port in use'}));const d=find(body.serial_ports[0]);if(body.action==='connect')active[d.device]=body.baud_rate;if(body.action==='disconnect')delete active[d.device];res.end(JSON.stringify({status:'success'}));});return;
 }
 if(req.url.endsWith('.png')){res.statusCode=204;return res.end();}res.setHeader('Content-Type','text/html');res.end(fs.readFileSync(root+'/serial_ports.html'));
});
(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));const b=await chromium.launch({headless:true,args:['--no-sandbox']});try{
 const p=await b.newPage();await p.goto('http://127.0.0.1:'+server.address().port);await p.getByRole('status').filter({hasText:'Connected · ESP-NOW Wi-Fi Master'}).waitFor();assert.equal(posts.length,0);
 const select=p.locator('#port-dropdown');assert.equal(await select.locator('option').count(),5);
 await select.selectOption('/dev/serial/by-id/espnow-receiver');await p.getByRole('button',{name:'Connect',exact:true}).click();await p.getByRole('status').filter({hasText:'Connected · ESP-NOW Receiver'}).waitFor();
 assert.equal(posts.at(-1).action,'connect');assert.deepEqual(posts.at(-1).serial_ports,['/dev/serial/by-id/espnow-receiver']);assert(active['/dev/ttyUSB8'],'Connecting another device must preserve current one');
 const before=posts.length;await p.getByRole('button',{name:'Pause Display',exact:true}).click();await p.getByRole('button',{name:'Resume Display',exact:true}).waitFor();assert.equal(posts.length,before);
 await p.getByRole('button',{name:'Disconnect',exact:true}).click();await p.getByRole('status').filter({hasText:'Disconnected · ESP-NOW Receiver'}).waitFor();assert.equal(posts.at(-1).action,'disconnect');assert.deepEqual(posts.at(-1).serial_ports,['/dev/ttyUSB9']);assert(active['/dev/ttyUSB8']);assert(await p.getByRole('button',{name:'Send Command',exact:true}).isDisabled());
 fail=true;await select.selectOption('/dev/serial/by-id/sms-text-gateway');await p.getByRole('button',{name:'Connect',exact:true}).click();await p.locator('#viewer-status').filter({hasText:'Port in use'}).waitFor();assert(await p.getByRole('button',{name:'Disconnect',exact:true}).isDisabled());
 const count=posts.length;await p.reload();await p.getByRole('status').filter({hasText:'Connected · ESP-NOW Wi-Fi Master'}).waitFor();assert.equal(posts.length,count);
 console.log('PASS: four stable names with renumbered ports; no automatic mutations; Connect preserves other devices; Pause never disconnects; targeted Disconnect works while paused; busy failure stays disconnected; reload does not connect. Synthetic hardware only.');
 }finally{await b.close();server.close();}})().catch(e=>{console.error(e);process.exitCode=1;server.close();});
