const $=s=>document.querySelector(s);
try {document.documentElement.dataset.theme=localStorage.getItem('folio-theme')||'light';}catch(e){}
$('#theme')?.addEventListener('click',()=>{const t=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=t;try{localStorage.setItem('folio-theme',t)}catch(e){}});
if(!matchMedia('(prefers-reduced-motion: reduce)').matches) document.querySelectorAll('[data-count]').forEach(el=>{const n=Number(el.dataset.count),start=performance.now();function tick(now){const p=Math.min((now-start)/750,1);el.textContent=Math.round(n*(1-Math.pow(1-p,3)));if(p<1)requestAnimationFrame(tick)}requestAnimationFrame(tick)});
const dialog=$('#bulk-dialog');
if(dialog){const tbody=$('#bulk-rows'), csv=$('#csv'), rowsPanel=$('#rows-panel'), csvPanel=$('#csv-panel');
function count(){ $('#row-count').textContent=rowsPanel.hidden?'CSV import':`${tbody.children.length} book rows`; }
function add(){if(tbody.children.length>=500)return;const tr=document.createElement('tr');tr.innerHTML='<td><input name="title" placeholder="Book title" required></td><td><input name="author" placeholder="Author" required></td><td><input name="category" placeholder="Category" required></td><td><input name="isbn" placeholder="ISBN"></td><td><input name="copies" type="number" min="1" max="1000000" value="1" required></td><td><button type="button" class="danger remove" aria-label="Remove row">×</button></td>';tbody.append(tr);count();}
add();add();add(); $('#add-row').onclick=add;tbody.onclick=e=>{if(e.target.closest('.remove')&&tbody.children.length>1){e.target.closest('tr').remove();count();}};
$('#open-bulk').onclick=()=>dialog.showModal();$('#close-bulk').onclick=()=>dialog.close();
document.querySelectorAll('[data-mode]').forEach(b=>b.onclick=()=>{const isCsv=b.dataset.mode==='csv';rowsPanel.hidden=isCsv;csvPanel.hidden=!isCsv;csv.disabled=!isCsv;csv.required=isCsv;tbody.querySelectorAll('input').forEach(i=>i.disabled=isCsv);document.querySelectorAll('[data-mode]').forEach(x=>x.classList.toggle('selected',x===b));count();});
$('#csv-file').onchange=async e=>{const f=e.target.files[0];if(f){if(f.size>250000){alert('CSV file is too large.');return;}csv.value=await f.text();}};
}
