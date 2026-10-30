(function(){
  var root=window.RECARCH_ROOT||'../',out=document.getElementById('out'),pick=document.getElementById('picker');
  function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  fetch(root+'data/systems.json').then(function(r){return r.json()}).then(function(all){
    var by={};all.forEach(function(c){by[c.id]=c});
    var ids=(new URLSearchParams(location.search).get('ids')||'').split(',').filter(function(i){return by[i]}).slice(0,3);
    pick.innerHTML='<div class="group"><b>Add</b><select id="add" class="search" style="max-width:420px"><option value="">Choose a system&hellip;</option>'+
      all.map(function(c){return '<option value="'+esc(c.id)+'">'+esc(c.name)+' ('+esc(c.company)+')</option>'}).join('')+'</select></div>';
    document.getElementById('add').addEventListener('change',function(e){
      if(!e.target.value)return;if(ids.indexOf(e.target.value)<0&&ids.length<3)ids.push(e.target.value);go()});
    function go(){location.search='?ids='+ids.join(',')}
    if(!ids.length){out.innerHTML='<div class="panel">Choose at least two systems above, or tick &ldquo;Compare&rdquo; on cards from the home page.</div>';return}
    var rows=[
      ['Company',function(c){return esc(c.company)}],['Surface',function(c){return esc(c.surface)}],['Year (first public)',function(c){return c.year+' ('+esc(c.first_public)+')'}],['Venue',function(c){return c.venue?esc(c.venue):'<span class="unk">preprint / blog only</span>'}],['Era',function(c){return esc(c.era)+'<div class="unk">'+esc(c.era_reason)+'</div>'}],
      ['Evidence',function(c){return esc(c.evidence_level.replace(/_/g,' '))}],
      ['Paradigms',function(c){return c.paradigms.map(function(p){return '<span class="tag">'+esc(p)+'</span>'}).join(' ')}],
      ['Stages',function(c){return c.stages.map(function(s){return '<div><b>'+esc(s.stage)+':</b> '+esc(s.model_family||'unknown')+'</div>'}).join('')}],
      ['ID / tokenization',function(c){return esc(c.id_tokenization.approach||'unknown')+(c.id_tokenization.details?'<div class="unk">'+esc(c.id_tokenization.details)+'</div>':'')}],
      ['Features',function(c){return c.features_signals.length?'<ul class="clean">'+c.features_signals.map(function(f){return '<li>'+esc(f)+'</li>'}).join('')+'</ul>':'<span class="unk">unknown</span>'}],
      ['Training',function(c){return esc(c.training.mode||'unknown')+'<div class="unk">'+esc((c.training.objectives||[]).join(', '))+'</div>'}],
      ['Serving',function(c){return c.serving_infra?esc(c.serving_infra):'<span class="unk">unknown</span>'}],
      ['Scale (stated)',function(c){return c.scale.length?'<ul class="clean">'+c.scale.map(function(s){return '<li>'+esc(s.metric)+': '+esc(s.value)+'</li>'}).join('')+'</ul>':'<span class="unk">none stated</span>'}],
      ['Results',function(c){return c.results_reported?esc(c.results_reported):'<span class="unk">unknown</span>'}],
      ['Code',function(c){var d=c.code;return '<div>'+esc(d.status.replace(/_/g,' '))+'</div>'+d.repos.map(function(r){return '<div><a target="_blank" rel="noopener nofollow" href="'+esc(r.url)+'">'+esc(r.url.replace('https://github.com/',''))+'</a>'+(r.official?'':' <span class="unk">(unofficial)</span>')+'</div>'}).join('')}],
      ['Caveats',function(c){return c.caveats.length?'<ul class="clean">'+c.caveats.map(function(s){return '<li>'+esc(s)+'</li>'}).join('')+'</ul>':'-'}],
      ['Sources',function(c){return '<ul class="clean">'+c.sources.map(function(s){return '<li><a target="_blank" rel="noopener nofollow" href="'+esc(s.url)+'">'+esc(s.title)+'</a></li>'}).join('')+'</ul>'}]
    ];
    var cs=ids.map(function(i){return by[i]});
    out.innerHTML='<div style="overflow-x:auto"><table class="cmp"><thead><tr><th></th>'+cs.map(function(c){return '<th><a href="'+root+'systems/'+esc(c.id)+'/">'+esc(c.name)+'</a></th>'}).join('')+'</tr></thead><tbody>'+
      rows.map(function(r){return '<tr><th>'+r[0]+'</th>'+cs.map(function(c){return '<td>'+r[1](c)+'</td>'}).join('')+'</tr>'}).join('')+'</tbody></table></div>';
    document.title='Compare: '+cs.map(function(c){return c.name}).join(' vs ')+' | RecArch';
  });
})();
