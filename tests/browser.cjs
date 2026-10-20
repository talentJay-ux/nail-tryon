const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium,webkit,devices}=require('playwright');
const engine=process.env.BROWSER||'chromium';
const base=process.env.BASE_URL||'http://127.0.0.1:8080/';
const output=path.resolve(__dirname,'../docs/validation');
async function main(){
  const browser=await (engine==='webkit'?webkit:chromium).launch({headless:true,
    ...(engine==='webkit'?(process.env.WEBKIT_EXECUTABLE?{executablePath:process.env.WEBKIT_EXECUTABLE}:{}):{executablePath:process.env.CHROMIUM_EXECUTABLE||'/usr/bin/chromium',args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']})});
  try{
    const context=await browser.newContext({...devices['iPhone 13'],deviceScaleFactor:1});
    const page=await context.newPage(),errors=[],requests=[];
    page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push({method:r.method(),url:r.url()}));
    await page.goto(base);
    assert.equal(await page.locator('#ovTitle').textContent(),'准备好了');
    assert.equal(await page.locator('#card .chip').count(),88);
    assert.equal(await page.locator('#shapeSeg button').count(),5);
    assert.equal(await page.locator('#patGrid button').count(),14);
    const report={engine,device:'iPhone 13 viewport; desktop host, not a physical iPhone',photos:{}};
    async function upload(name){
      const t=Date.now();await page.setInputFiles('#file',path.join(__dirname,'fixtures',name+'.jpg'));
      await page.waitForFunction(()=>!document.getElementById('snapBtn').disabled||document.getElementById('stHands').textContent.includes('处理失败'),null,{timeout:120000});
      const readyMs=Date.now()-t;
      await page.waitForFunction(()=>document.getElementById('viewer').dataset.fingers==='done',null,{timeout:60000});
      const state=await page.evaluate(()=>({nails:nails.length,hands:lastHands.length,matched:nails.filter(n=>n.f>=0).length,status:$('stHands').textContent,error:!$('overlay').hidden?$('ovText').textContent:null}));
      assert.equal(state.error,null,'model must run, not silently fall back to landmark rectangles');
      return{...state,readyMs,withFingerLabelsMs:Date.now()-t};
    }
    for(const [name,count]of[['cup',8],['two-hands',6],['almond-long',5],['crossed',2]]){
      report.photos[name]=await upload(name);assert.equal(report.photos[name].nails,count,name);
      const clean=await page.evaluate(()=>{draw(false);return cv.toDataURL('image/jpeg',.92)});
      if(engine==='chromium')fs.writeFileSync(path.join(output,name+'-after.jpg'),Buffer.from(clean.split(',')[1],'base64'));
      const clipping=await page.evaluate(()=>{
        draw(false);const union=document.createElement('canvas');union.width=cv.width;union.height=cv.height;const u=union.getContext('2d');
        for(const n of nailFrames()){u.save();frameTransform(u,n);drawInstanceMask(u,n);u.restore()}
        const a=u.getImageData(0,0,cv.width,cv.height).data,b=photo.getContext('2d').getImageData(0,0,cv.width,cv.height).data,c=ctx.getImageData(0,0,cv.width,cv.height).data;
        let outside=0,changed=0;for(let i=0;i<a.length;i+=4){if(Math.abs(b[i]-c[i])+Math.abs(b[i+1]-c[i+1])+Math.abs(b[i+2]-c[i+2])>3){changed++;if(a[i+3]===0)outside++}}
        return{outside,changed};
      });
      assert.equal(clipping.outside,0,'painting must stay within actual instance masks');assert.ok(clipping.changed>100);
      report.photos[name].clipping=clipping;
      if(name==='cup')await page.screenshot({path:path.join(output,engine+'-mobile-cup.png')});
    }
    // No-hand nails use the all-fingers design and still support instance corrections.
    await upload('cup');assert.equal(await page.evaluate(()=>lastHands.length),0);
    const target=await page.evaluate(()=>({id:nails[0].id,x:nails[0].mx,y:nails[0].my}));
    const rect=await page.locator('#cv').boundingBox();const size=await page.evaluate(()=>({w:cv.width,h:cv.height}));
    const x=rect.x+target.x/size.w*rect.width,y=rect.y+target.y/size.h*rect.height;
    await page.mouse.move(x,y);await page.mouse.down();await page.mouse.move(x+12,y+8);await page.mouse.up();
    const correction=await page.evaluate(id=>({selected:sel,dx:adjOf(id).dx,dy:adjOf(id).dy,scope:st.scope}),target.id);
    assert.equal(correction.selected,target.id);assert.equal(correction.scope,'all');assert.ok(correction.dx>10&&correction.dy>5);
    await page.click('[data-t="pos"]');
    const width=await page.evaluate(id=>frames.find(n=>n.id===id).w,target.id);
    await page.locator('#adjW').evaluate(e=>{e.value=120;e.dispatchEvent(new Event('input',{bubbles:true}))});
    assert.ok(Math.abs((await page.evaluate(id=>frames.find(n=>n.id===id).w,target.id))/width-1.2)<.001);
    await page.click('#resetBtn');assert.equal(await page.evaluate(()=>adjOf(sel).dx),0);
    // Hand labels drive per-finger designs without changing the fallback "all" design.
    await upload('almond-long');assert.equal(await page.evaluate(()=>nails.filter(n=>n.f>=0).length),5);
    await page.click('#fingerSel [data-i="1"]');const rest=await page.evaluate(()=>st.rest.color);
    await page.click('[data-t="card"]');await page.click('#card [data-c="#F9D9E0"]');
    assert.equal(await page.evaluate(()=>st.per[1].color),'#F9D9E0');assert.equal(await page.evaluate(()=>st.rest.color),rest);
    await page.click('[data-t="pat"]');await page.click('#patGrid [data-k="french"]');await page.click('#decSeg [data-k="pearl"]');
    await page.click('[data-t="fin"]');await page.click('#finSeg [data-k="cateye"]');await page.click('#shapeSeg [data-k="almond"]');await page.click('#lenSeg [data-k="medium"]');
    const expected=await page.evaluate(()=>{st.showSeg=true;st.showPts=true;const seg=st.showSeg;st.showSeg=false;draw(false);const im=cv.toDataURL('image/jpeg',.92);st.showSeg=seg;return im});
    await page.click('#snapBtn');assert.equal(await page.locator('#shotImg').getAttribute('src'),expected,'export excludes selection, mask debug and landmarks');
    const text=await page.locator('#sheetText').inputValue();for(const word of ['P01','法式','珍珠','猫眼','杏仁形','延长一点'])assert.ok(text.includes(word),word);
    await page.click('#shotClose');
    // Cached outputs support threshold edits without a second neural network run.
    await upload('two-hands');await page.click('[data-t="pos"]');
    await page.locator('#conf').evaluate(e=>{e.value=70;e.dispatchEvent(new Event('input',{bubbles:true}))});
    await page.waitForFunction(()=>nails.length===5);assert.equal(await page.evaluate(()=>nails.length),5);
    // A new blank image must clear stale nails, even when Hands cannot find a hand.
    const blank=await page.evaluate(()=>{const c=document.createElement('canvas');c.width=c.height=640;const g=c.getContext('2d');g.fillStyle='#999';g.fillRect(0,0,640,640);return c.toDataURL('image/png')});
    await page.setInputFiles('#file',{name:'blank.png',mimeType:'image/png',buffer:Buffer.from(blank.split(',')[1],'base64')});
    await page.waitForFunction(()=>document.getElementById('viewer').dataset.fingers==='done');assert.equal(await page.evaluate(()=>nails.length),0);
    assert.ok(requests.every(r=>r.method==='GET'),'photo data is never uploaded');
    assert.deepEqual(errors,[]);
    report.functional='PASS: clipping, unknown-finger design, drag, correction/reset, single-finger editing, pattern/finish/decor/shape/extension, clean image/text export, threshold re-decode, stale-state clearing, local-only photos';
    fs.writeFileSync(path.join(output,engine+'-results.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
  }finally{await browser.close()}
}
main().catch(e=>{console.error(e);process.exitCode=1});
