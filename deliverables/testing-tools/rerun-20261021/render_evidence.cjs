const fs = require('fs');
const path = require('path');
const { chromium } = require('/home/sujith/Documents/SIS-Karpathy-Map/sis-app/frontend/node_modules/playwright');
(async()=>{
 const root='/home/sujith/Documents/SIS-Karpathy-Map/deliverables/testing-tools/rerun-20261021';
 const out='/home/sujith/Documents/SIS-Karpathy-Map/deliverables/screenshots/tool-verification/rerun-20261021';
 const raw=JSON.parse(fs.readFileSync(root+'/postman/run.json','utf8'));
 const run=raw.run||{}; const stats=run.stats||{}; const execs=run.executions||[];
 const checks=[];
 for(const e of execs){ for(const a of (e.assertions||[])) checks.push({name:a.assertion,ok:!a.error&&!a.skipped,request:e.item?.name||'Request'}); }
 const fail=checks.filter(x=>!x.ok).length;
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const items=execs.map(e=>`<tr><td>${esc(e.item?.name)}</td><td>${esc(e.request?.method)}</td><td>${esc(e.response?.code??'NO RESPONSE')}</td><td>${esc(e.response?.responseTime??'—')} ms</td><td>${(e.assertions||[]).every(a=>!a.error&&!a.skipped)?'<b class="pass">PASS</b>':'<b class="fail">CHECK</b>'}</td></tr>`).join('');
 const html=`<!doctype html><html><head><meta charset="utf-8"><title>Newman · Postman collection execution evidence</title><style>*{box-sizing:border-box}body{margin:0;background:#f3f5f8;color:#15253c;font:15px/1.5 Inter,system-ui,sans-serif}.top{background:#10223d;color:#fff;padding:32px 44px;border-bottom:5px solid #a8e85b}.top small{color:#b9c6d8;letter-spacing:.12em;text-transform:uppercase}.top h1{font-size:29px;margin:7px 0}.wrap{padding:28px 44px;max-width:1400px;margin:auto}.meta{color:#52627a}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:22px 0}.card{background:white;border:1px solid #dce3ec;border-radius:10px;padding:19px}.card span{display:block;color:#61718a;font-size:12px;text-transform:uppercase;letter-spacing:.08em}.card strong{font-size:31px}.pass{color:#19764a}.fail{color:#b42318}table{width:100%;border-collapse:collapse;background:white;border:1px solid #dce3ec;border-radius:10px;overflow:hidden}th,td{text-align:left;padding:13px 15px;border-bottom:1px solid #e5eaf1}th{background:#eaf0f6;font-size:12px;text-transform:uppercase;letter-spacing:.06em}footer{margin-top:20px;color:#61718a;font-size:12px}</style></head><body><header class="top"><small>API verification · real execution output</small><h1>Postman collection — Newman run</h1><div>Collection: SIS — Functional API Verification</div></header><main class="wrap"><div class="meta">Executed ${new Date().toLocaleString('en-IN',{timeZone:'Asia/Kolkata',dateStyle:'medium',timeStyle:'long'})} · Target: http://127.0.0.1:8000 · Synthetic test account only</div><section class="cards"><div class="card"><span>Requests</span><strong>${stats.requests?.total??execs.length}</strong></div><div class="card"><span>Assertions</span><strong>${stats.assertions?.total??checks.length}</strong></div><div class="card"><span>Assertion failures</span><strong class="${fail?'fail':'pass'}">${fail}</strong></div><div class="card"><span>Average response</span><strong>${Math.round(run.timings?.responseAverage??0)}<small> ms</small></strong></div></section><h2>Request-by-request evidence</h2><table><thead><tr><th>Collection item</th><th>Method</th><th>HTTP status</th><th>Elapsed</th><th>Assertions</th></tr></thead><tbody>${items}</tbody></table><footer>Rendered directly from the Newman JSON reporter output for this run. This is an evidence summary, not a screenshot of the Postman desktop application. Response bodies, credentials and bearer tokens are intentionally not shown.</footer></main></body></html>`;
 fs.writeFileSync(out+'/postman-newman-run.html',html);
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 for(const [file,png,fullPage] of [
  [out+'/postman-newman-run.html',out+'/postman-newman-run.png',true],
  [root+'/jmeter-baseline/html-report/index.html',out+'/jmeter-baseline-dashboard.png',true],
  [root+'/jmeter-overload/html-report/index.html',out+'/jmeter-overload-dashboard.png',true]
 ]) { const page=await browser.newPage({viewport:{width:1600,height:1100},deviceScaleFactor:1}); await page.goto('file://'+file,{waitUntil:'networkidle',timeout:30000}); await page.screenshot({path:png,fullPage,animations:'disabled'}); console.log('SCREENSHOT',png,await page.locator('body').innerText().then(t=>t.slice(0,180).replace(/\s+/g,' '))); await page.close(); }
 await browser.close();
 console.log('POSTMAN_STATS',JSON.stringify(stats),'CHECKS',checks.length,'FAILED',fail);
})();
