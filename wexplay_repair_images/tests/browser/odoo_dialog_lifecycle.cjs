const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const moduleRoot = path.resolve(__dirname, '../..');
const webRoot = process.env.ODOO_WEB_PATH || 'C:/Program Files/Odoo 18.0.20260220/server/odoo/addons/web/static';
const read = relative => fs.readFileSync(path.join(webRoot, relative), 'utf8');
const strip = source => source.replace(/^import .*;$/gm, '').replaceAll('export class', 'class').replaceAll('export const', 'const');
(async () => {
    const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true });
    const watchdog = setTimeout(() => { console.error('FAIL: dialog lifecycle timeout'); browser.close().finally(() => process.exit(1)); }, 15000);
    try {
        const page = await browser.newPage();
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        await page.setContent('<div id="app"></div>');
        await page.addScriptTag({ path: path.join(webRoot, 'lib/owl/owl.js') });
        await page.addScriptTag({ path: path.join(moduleRoot, 'static/lib/filerobot/filerobot-image-editor-4.8.1.min.js') });
        let dialog = strip(read('src/core/dialog/dialog.js'));
        dialog = dialog.slice(dialog.indexOf('class Dialog'));
        const component = strip(fs.readFileSync(path.join(moduleRoot, 'static/src/js/repair_media_upload_dialog.js'), 'utf8'));
        const services = ['overlay/overlay_container.js', 'overlay/overlay_service.js', 'dialog/dialog_service.js'].map(p => strip(read('src/core/' + p))).join('\n');
        await page.addScriptTag({ content: `
            const {Component,onMounted,onWillUnmount,onWillDestroy,useRef,useState,useEffect,useChildSubEnv,useExternalListener,markRaw,reactive,xml}=owl;
            const useHotkey=()=>{}, useActiveElement=()=>{}, useForwardRefToParent=()=>useRef('modalRef'), useDialogDraggable=()=>{}, throttleForAnimation=f=>f;
            const loadJS=async()=>{}, sortBy=(arr,fn)=>arr.sort((a,b)=>fn(a)-fn(b));
            const registry={category:()=>({add:()=>{}})};
            class ErrorHandler extends Component {static template=xml\`<t t-slot="default"/>\`;static props=['*'];}
            ${dialog}\n${component}\n${services}
            window.testClasses={OverlayContainer,overlayService,dialogService,RepairMediaUploadDialog};
        ` });
        const inner = xml => xml.replace(/<\?xml[^>]+>/, '').replace(/<templates[^>]*>/, '').replace('</templates>', '');
        const templates = '<templates>' + [read('src/core/dialog/dialog.xml'), read('src/core/overlay/overlay_container.xml'), fs.readFileSync(path.join(moduleRoot, 'static/src/xml/repair_media_upload_dialog.xml'), 'utf8')].map(inner).join('') + '</templates>';
        await page.addStyleTag({ path: path.join(webRoot, 'lib/bootstrap/dist/css/bootstrap.css') });
        const css = require('child_process').execFileSync(process.env.ODOO_PYTHON || 'C:/Program Files/Odoo 18.0.20260220/python/python.exe', ['-c', 'import sass,sys; print(sass.compile(filename=sys.argv[1]))', path.join(moduleRoot, 'static/src/scss/repair_media_upload_dialog.scss')], {encoding:'utf8'});
        await page.addStyleTag({ content: css + '.o_modal_full .modal-dialog{width:100%;max-width:none;height:100%;margin:0}' });
        await page.evaluate(async templates => {
            const {OverlayContainer,overlayService,dialogService,RepairMediaUploadDialog}=testClasses;
            window.overlay=overlayService.start(); window.dialog=dialogService.start({}, {overlay});
            window.app=new owl.App(OverlayContainer,{templates,props:{overlays:overlay.overlays},env:{isSmall:false}});
            await app.mount(document.getElementById('app'));
            const canvas=document.createElement('canvas');canvas.width=1714;canvas.height=2048;
            const ctx=canvas.getContext('2d');ctx.fillStyle='#354e68';ctx.fillRect(0,0,1714,2048);ctx.fillStyle='#ddd';ctx.fillRect(200,300,900,1200);
            const blob=await new Promise(resolve=>canvas.toBlob(resolve));
            window.file=new File([blob],'test.png',{type:'image/png'});
            window.uploads=0; window.releaseUpload=null;
            window.open=()=>dialog.add(RepairMediaUploadDialog,{
                files:[file],uploadFile:(file)=>new Promise(resolve=>{window.lastFile=file;uploads++;releaseUpload=resolve;}),onUploaded:async()=>{},
            });
            open();
        }, templates);
        await page.waitForSelector('.FIE_root canvas');
        await page.waitForTimeout(250);
        await page.locator('[aria-label="Close"]').click();
        await page.waitForSelector('.o_dialog', { state: 'detached' });
        await page.evaluate(() => open());
        await page.waitForSelector('.FIE_root canvas');
        await page.waitForTimeout(250);
        const sidebar = await page.locator('.FIE_tabs').evaluate(el=>({width:el.clientWidth,scroll:el.scrollWidth}));
        if(sidebar.scroll>sidebar.width) throw new Error('Sidebar has horizontal overflow');
        const icon=await page.locator('.FIE_tab svg').first().boundingBox();
        const tab=await page.locator('.FIE_tab').first().boundingBox();
        if(Math.abs(icon.x+icon.width/2-tab.x-tab.width/2)>1) throw new Error('Sidebar icon is not centered');
        const gallery=await page.locator('.wex-media-upload__gallery').boundingBox();
        const description=await page.locator('textarea').boundingBox();
        const bottom=await page.locator('.wex-media-upload__bottom').boundingBox();
        if(gallery.y+gallery.height>description.y || description.width<bottom.width-2) throw new Error('Gallery/description must stack at full width');
        const canvasArea=await page.locator('.FIE_canvas-container').boundingBox();
        if(canvasArea.height < page.viewportSize().height * .45) throw new Error('Editor image area is too short: '+canvasArea.height);
        await page.getByText('Pintar', {exact:true}).click();
        await page.waitForSelector('.wex-pen-controls');
        const width = page.getByLabel('Grosor del pincel', {exact:true});
        await width.fill('12');
        await page.getByLabel('Color del pincel', {exact:true}).fill('#00ff00');
        await page.waitForTimeout(200);
        if (await page.getByText('12 px',{exact:true}).count() !== 1) throw new Error('Brush size did not update');
        const box=await page.locator('.konvajs-content').boundingBox();
        await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();
        await page.mouse.move(box.x+box.width/2+30,box.y+box.height/2+30,{steps:10});await page.mouse.up();
        await page.screenshot({path:path.join(require('os').tmpdir(), 'wex-media-desktop.png')});
        await page.locator('.modal-footer .btn-primary').click();
        await page.waitForFunction(() => uploads === 1);
        await page.locator('[aria-label="Close"]').click();
        if (await page.locator('.o_dialog').count() !== 1) throw new Error('Closed while upload in progress');
        const hasGreenStroke=await page.evaluate(async()=>{
            const bitmap=await createImageBitmap(lastFile); const c=document.createElement('canvas');c.width=bitmap.width;c.height=bitmap.height;
            const ctx=c.getContext('2d');ctx.drawImage(bitmap,0,0);bitmap.close(); const data=ctx.getImageData(0,0,c.width,c.height).data;
            for(let i=0;i<data.length;i+=4) if(data[i]<20&&data[i+1]>230&&data[i+2]<20&&data[i+3]===255) return true;
            return false;
        });
        if(!hasGreenStroke) throw new Error('Brush color was not exported as an opaque stroke');
        await page.evaluate(() => releaseUpload());
        await page.waitForSelector('.o_dialog', { state: 'detached' });
        await page.setViewportSize({width:390,height:844});
        await page.evaluate(()=>open());
        await page.waitForSelector('.FIE_root canvas');
        await page.waitForTimeout(250);
        const toggle=page.locator('.FIE_tabs_toggle_btn');
        if(await toggle.isVisible()) await toggle.click();
        await page.getByText('Pintar',{exact:true}).click();
        await page.waitForSelector('.wex-pen-controls');
        await page.waitForTimeout(300);
        await page.screenshot({path:path.join(require('os').tmpdir(),'wex-media-mobile.png')});
        await page.locator('[aria-label="Close"]').first().click();
        await page.waitForSelector('.o_dialog',{state:'detached'});
        if (errors.length) throw new Error(errors.join('\n'));
        console.log('PASS: real Odoo overlay/dialog services, open, close, reopen, upload and busy-close guard');
    } finally {
        clearTimeout(watchdog);
        await browser.close();
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
