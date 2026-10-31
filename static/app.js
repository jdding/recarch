(function(){
  var _L=window.RECARCH_L10N||{};function L(k,d,o){var s=_L[k]!=null?_L[k]:d;return o?s.replace(/\{(\w+)\}/g,function(m,x){return o[x]}):s}
  var cards=[].slice.call(document.querySelectorAll('.card')),
      tl=[].slice.call(document.querySelectorAll('.tl-item')),
      q=document.getElementById('q'),count=document.getElementById('count'),empty=document.getElementById('empty'),
      prod=document.getElementById('f-prod'),off=document.getElementById('f-official'),more=document.getElementById('more'),
      grid=document.getElementById('grid'),sortSel=document.getElementById('sort'),timeline=document.getElementById('timeline'),
      GROUPS=['era','stage','family','paradigm','evidence'],sel={},cmp=new Set(),view='list',total=cards.length;
  GROUPS.forEach(function(g){sel[g]=new Set()});
  function match(el){
    var d=el.dataset,t=(q.value||'').toLowerCase().trim();
    if(t&&d.search.indexOf(t)<0)return false;
    if(prod.checked&&d.prod!=='1')return false;
    if(off.checked&&d.official!=='1')return false;
    var m={era:[d.era],stage:d.stages.split('|'),family:d.families.split('|'),paradigm:d.paradigms.split('|'),evidence:[d.evidence]};
    for(var i=0;i<GROUPS.length;i++){var g=GROUPS[i];
      if(sel[g].size&&!m[g].some(function(x){return sel[g].has(x)}))return false}
    return true;
  }
  function active(){
    var n=(q.value.trim()?1:0)+(prod.checked?1:0)+(off.checked?1:0);GROUPS.forEach(function(g){n+=sel[g].size});return n;
  }
  function apply(){
    var n=0;
    cards.forEach(function(c){var ok=match(c);c.hidden=!ok;if(ok)n++});
    tl.forEach(function(c){c.hidden=!match(c)});
    [].forEach.call(document.querySelectorAll('.tl-row'),function(r){
      r.hidden=!r.querySelector('.tl-item:not([hidden])');
      [].forEach.call(r.querySelectorAll('.tl-cell'),function(cell){cell.classList.toggle('empty',!cell.querySelector('.tl-item:not([hidden])'))})});
    count.textContent=(n===total?L('count_all','{n} systems',{n:total}):L('count_some','{n} of {t} systems',{n:n,t:total}));
    empty.hidden=n>0;
    document.getElementById('reset').hidden=active()===0;
    var parts=[];
    function add(k,v){parts.push(k+'='+v)}
    if(q.value)add('q',encodeURIComponent(q.value));
    GROUPS.forEach(function(g){if(sel[g].size)add(g,Array.from(sel[g]).map(encodeURIComponent).join(','))});
    if(prod.checked)add('prod','1');if(off.checked)add('official','1');
    if(view==='timeline')add('view','timeline');
    if(sortSel.value!=='default')add('sort',sortSel.value);
    history.replaceState(null,'',parts.length?'?'+parts.join('&'):location.pathname);
  }
  cards.forEach(function(c,i){c.dataset.idx=i});
  function applySort(){
    var list=cards.slice();
    if(sortSel.value==='cites')list.sort(function(a,b){
      var x=a.dataset.cites,y=b.dataset.cites,hx=x!==undefined,hy=y!==undefined;
      if(hx!==hy)return hx?-1:1;                       // cards without a count (blog/code only) go last, never as 0
      if(hx&&+x!==+y)return +y-+x;return +a.dataset.idx-+b.dataset.idx});
    list.forEach(function(c){grid.appendChild(c)});
  }
  function setView(v){
    view=v;document.getElementById('sortwrap').hidden=v!=='list';grid.hidden=v!=='list';timeline.hidden=v!=='timeline';
    document.getElementById('cmpbar').style.display=(v==='list'&&cmp.size)?'flex':'none';
    [].forEach.call(document.querySelectorAll('.seg button'),function(b){b.setAttribute('aria-pressed',String(b.dataset.view===v))});
  }
  function syncChip(g,v,on){
    var b=document.querySelector('.group[data-group='+g+'] .chip[data-v="'+v.replace(/"/g,'\\"')+'"]');if(b)b.setAttribute('aria-pressed',String(on));
  }
  document.querySelectorAll('.group[data-group]').forEach(function(grp){
    grp.addEventListener('click',function(e){var b=e.target.closest('.chip');if(!b)return;
      var g=grp.dataset.group,v=b.dataset.v;
      if(sel[g].has(v)){sel[g].delete(v);syncChip(g,v,false)}else{sel[g].add(v);syncChip(g,v,true)}
      apply()});
  });
  sortSel.addEventListener('change',function(){applySort();apply()});
  q.addEventListener('input',apply);prod.addEventListener('change',apply);off.addEventListener('change',apply);
  function clearAll(){
    q.value='';prod.checked=false;off.checked=false;GROUPS.forEach(function(g){sel[g].clear()});
    document.querySelectorAll('.chip[aria-pressed=true]').forEach(function(b){b.setAttribute('aria-pressed','false')});apply()}
  document.getElementById('reset').addEventListener('click',clearAll);
  document.getElementById('reset2').addEventListener('click',clearAll);
  document.querySelector('.seg').addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;setView(b.dataset.view);apply()});
  var p=new URLSearchParams(location.search);
  if(p.get('q'))q.value=p.get('q');
  GROUPS.forEach(function(g){(p.get(g)||'').split(/[|,]/).filter(Boolean).forEach(function(v){sel[g].add(v);syncChip(g,v,true)})});
  prod.checked=p.get('prod')==='1';off.checked=p.get('official')==='1';
  if(sel.paradigm.size||sel.evidence.size)more.open=true;
  if(p.get('sort')==='cites')sortSel.value='cites';applySort();
  setView(p.get('view')==='timeline'?'timeline':'list');
  apply();
  var bar=document.getElementById('cmpbar');
  document.addEventListener('change',function(e){
    if(!e.target.classList.contains('cmp'))return;
    var id=e.target.closest('.card').dataset.id;
    if(e.target.checked){if(cmp.size>=3){e.target.checked=false;alert(L('cmp_max','Compare up to 3 systems.'));return}cmp.add(id)}else cmp.delete(id);
    bar.style.display=cmp.size?'flex':'none';
    document.getElementById('cmpn').textContent=L('selected','{n} selected',{n:cmp.size});
    document.getElementById('cmplink').href='compare/?ids='+Array.from(cmp).join(',');
  });
})();
