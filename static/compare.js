(function(){
  var root=window.RECARCH_ROOT||'../',out=document.getElementById('out'),pick=document.getElementById('picker');
  var _L=window.RECARCH_L10N||{};
  function L(k,d,o){var s=_L[k]!=null?_L[k]:d;return o?s.replace(/\{(\w+)\}/g,function(m,x){return o[x]}):s}
  function M(map,k,d){return (_L[map]&&_L[map][k])||d}
  var SEP=_L.lang==='zh'?'\u3001':', ';
  function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
  fetch(root+'data/systems.json').then(function(r){return r.json()}).then(function(all){
    var by={};all.forEach(function(c){by[c.id]=c});
    var ids=(new URLSearchParams(location.search).get('ids')||'').split(',').filter(function(i){return by[i]}).slice(0,3);
    pick.innerHTML='<div class="group"><b>'+esc(L('cmp_add','Add'))+'</b><select id="add" class="search" style="max-width:420px"><option value="">'+esc(L('cmp_choose','Choose a system\u2026'))+'</option>'+
      all.map(function(c){return '<option value="'+esc(c.id)+'">'+esc(L('cmp_option','{name} ({company})',{name:c.name,company:c.company}))+'</option>'}).join('')+'</select></div>';
    document.getElementById('add').addEventListener('change',function(e){
      if(!e.target.value)return;if(ids.indexOf(e.target.value)<0&&ids.length<3)ids.push(e.target.value);go()});
    function go(){location.search='?ids='+ids.join(',')}
    if(!ids.length){out.innerHTML='<div class="panel">'+esc(L('cmp_empty','Choose at least two systems above, or tick \u201cCompare\u201d on cards from the home page.'))+'</div>';return}
    var unk='<span class="unk">'+esc(L('unknown','unknown'))+'</span>';
    var nr='<span class="unk">'+esc(L('nr','not reported'))+'</span>';
    function dep(c,k,f){var d=c.deployment;if(!d||d[k]==='not_reported')return nr;return f?f(d[k]):esc(d[k])}
    var rows=[
      [L('row_company','Company'),function(c){return esc(c.company)}],[L('row_surface','Surface'),function(c){return esc(c.surface)}],[L('row_year','Year (first public)'),function(c){return esc(L('year_fmt','{y} ({m})',{y:c.year,m:c.first_public}))}],[L('row_venue','Venue'),function(c){return c.venue?esc(c.venue):'<span class="unk">'+esc(L('preprint','preprint / blog only'))+'</span>'}],[L('row_era','Era'),function(c){return esc(M('era',c.era,c.era))+'<div class="unk">'+esc(c.era_reason)+'</div>'}],
      [L('row_evidence','Evidence'),function(c){return esc(M('evid',c.evidence_level,c.evidence_level.replace(/_/g,' ')))}],
      [L('row_paradigms','Paradigms'),function(c){return c.paradigms.map(function(p){return '<span class="tag">'+esc(p)+'</span>'}).join(' ')}],
      [L('row_stages','Stages'),function(c){return c.stages.map(function(s){return '<div><b>'+esc(M('stage',s.stage,s.stage))+':</b> '+(s.model_family?esc(s.model_family):esc(L('unknown','unknown')))+'</div>'}).join('')}],
      [L('row_idtok','ID / tokenization'),function(c){return (c.id_tokenization.approach?esc(c.id_tokenization.approach):esc(L('unknown','unknown')))+(c.id_tokenization.details?'<div class="unk">'+esc(c.id_tokenization.details)+'</div>':'')}],
      [L('row_features','Features'),function(c){return c.features_signals.length?'<ul class="clean">'+c.features_signals.map(function(f){return '<li>'+esc(f)+'</li>'}).join('')+'</ul>':unk}],
      [L('row_training','Training'),function(c){return (c.training.mode?esc(c.training.mode):esc(L('unknown','unknown')))+'<div class="unk">'+esc((c.training.objectives||[]).join(SEP))+'</div>'}],
      [L('row_serving','Serving'),function(c){return c.serving_infra?esc(c.serving_infra):unk}],
      [L('row_scale','Scale (stated)'),function(c){return c.scale.length?'<ul class="clean">'+c.scale.map(function(s){return '<li>'+esc(s.metric)+': '+esc(s.value)+'</li>'}).join('')+'</ul>':'<span class="unk">'+esc(L('none_stated','none stated'))+'</span>'}],
      [L('row_online_evidence','Online evidence'),function(c){return dep(c,'online_evidence',function(v){return esc(M('depev',v,v))})}],
      [L('row_lifts','Online lifts'),function(c){var d=c.deployment;return d&&d.online_lifts!=='not_reported'?'<ul class="clean">'+d.online_lifts.map(function(x){return '<li>'+esc(x.metric)+': <b>'+esc(x.value)+'</b></li>'}).join('')+'</ul>':nr}],
      [L('row_ab_traffic','A/B traffic'),function(c){return dep(c,'ab_traffic')}],[L('row_ab_duration','A/B duration'),function(c){return dep(c,'ab_duration')}],
      [L('row_latency','Serving latency'),function(c){return dep(c,'serving_latency')}],[L('row_cost','Inference cost'),function(c){return dep(c,'inference_cost')}],[L('row_hardware','Hardware'),function(c){return dep(c,'hardware')}],
      [L('row_results','Results'),function(c){return c.results_reported?esc(c.results_reported):unk}],
      [L('row_code','Code'),function(c){var d=c.code;return '<div>'+esc(M('code',d.status,d.status.replace(/_/g,' ')))+'</div>'+d.repos.map(function(r){return '<div><a target="_blank" rel="noopener nofollow" href="'+esc(r.url)+'">'+esc(r.url.replace('https://github.com/',''))+'</a>'+(r.official?'':' <span class="unk">'+esc(L('unofficial_tag','(unofficial)'))+'</span>')+'</div>'}).join('')}],
      [L('row_caveats','Caveats'),function(c){return c.caveats.length?'<ul class="clean">'+c.caveats.map(function(s){return '<li>'+esc(s)+'</li>'}).join('')+'</ul>':'-'}],
      [L('row_sources','Sources'),function(c){return '<ul class="clean">'+c.sources.map(function(s){return '<li><a target="_blank" rel="noopener nofollow" href="'+esc(s.url)+'">'+esc(s.title)+'</a></li>'}).join('')+'</ul>'}]
    ];
    var cs=ids.map(function(i){return by[i]});
    out.innerHTML='<div style="overflow-x:auto"><table class="cmp"><thead><tr><th></th>'+cs.map(function(c){return '<th><a href="'+root+'systems/'+esc(c.id)+'/">'+esc(c.name)+'</a></th>'}).join('')+'</tr></thead><tbody>'+
      rows.map(function(r){return '<tr><th>'+esc(r[0])+'</th>'+cs.map(function(c){return '<td>'+r[1](c)+'</td>'}).join('')+'</tr>'}).join('')+'</tbody></table></div>';
    document.title=L('cmp_title','Compare: {names} | RecArch',{names:cs.map(function(c){return c.name}).join(' vs ')});
  });
})();
