import gzip,xml.etree.ElementTree as ET,json,datetime,collections,re,html,os
from pathlib import Path
from zoneinfo import ZoneInfo
paths=[(str(Path(__file__).parent/'data'/'GR.xml.gz'),'GR'),(str(Path(__file__).parent/'data'/'CY.xml.gz'),'CY')]
TZ=ZoneInfo('Europe/Athens')
start=datetime.datetime.now(TZ).replace(hour=0,minute=0,second=0,microsecond=0)
end=start+datetime.timedelta(days=3)
start_ts=int(start.timestamp()//60)
end_ts=int(end.timestamp()//60)
channels=[]; programmes=collections.defaultdict(list)
for path,country in paths:
 with gzip.open(path,'rb') as f:
  for ev,e in ET.iterparse(f,events=('end',)):
   if e.tag=='channel':
    name=e.findtext('display-name') or e.get('id','')
    icons=e.findall('icon'); icon=icons[0].get('src','') if icons else ''
    channels.append({'id':e.get('id'),'name':name,'country':country,'icon':icon})
    e.clear()
   elif e.tag=='programme':
    try:
     def parse_stamp(v):return datetime.datetime.strptime(v,'%Y%m%d%H%M%S %z')
     a=int(parse_stamp(e.attrib['start']).timestamp()//60);b=int(parse_stamp(e.attrib['stop']).timestamp()//60)
     if b<=start_ts or a>=end_ts or b<=a: e.clear();continue
     title=(e.findtext('title') or '').strip()
     desc=(e.findtext('desc') or '').strip()
     cats=[(c.text or '').strip() for c in e.findall('category') if c.text]
     programmes[e.attrib['channel']].append([a-start_ts,b-start_ts,title,desc[:260],'/'.join(cats[:2])])
    except Exception:pass
    e.clear()
# remove channels with no programs in dates, show only if programs? show all toggle no data later
for c in channels:
 c['events']=sorted(programmes[c['id']],key=lambda e:e[0]);
 if 'Magenta' in c['name'] or 'COSMOTE' in c['name']:c['provider']='MAGENTA'
 elif 'Nova' in c['name'] or 'Novasport' in c['name']:c['provider']='NOVA'
 elif c['id'] in ('Antenna.Comedy.gr','Antenna.Drama.gr','Sports.1.gr','Sports.2.gr','Sports.3.gr','Fight.gr','PadelTime.gr'):c['provider']='ANT1+'
 elif 'Cytavision' in c['name']:c['provider']='CYTAVISION'
 elif 'Cablenet' in c['name']:c['provider']='CABLENET'
 else:c['provider']='GR' if c['country']=='GR' else 'CY'
 name=c['name'].lower();cid=c['id'].lower()
 if re.search('sport|formula|eurosport|aek|ολυμπια|παναθηνα|golf|racing|fight|padel|cytavision|cablenet.sports',name+' '+cid):typ='sport'
 elif re.search('cinema|movie|film|village|oscars|tcm',name):typ='film'
 elif re.search('history|geographic|nat.geo|discovery|viasat|bbc.earth|animal|investigation|crime|travel|docu|planet|science|museum|nature|explore',name+' '+cid):typ='doc'
 elif re.search('disney|nickelodeon|baby|cartoon|boomerang|duck|smile|junior|kids|da vinci',name+' '+cid):typ='kids'
 elif re.search('mad|music|mtv|mezzo|stingray|jazz|concert|classica|panik|nr1|greekz',name+' '+cid):typ='music'
 elif re.search('news|euronews|cnn|bloomberg|cnbc|dw|france 24|al jazeera|sky news|ναυτεμπορ|ert.news',name+' '+cid):typ='news'
 elif re.search('series|drama|comedy|fox|fx|novalife|epicdrama',name+' '+cid):typ='series'
 else:typ='general'
 c['type']=typ
# collapse only channels same normalized name with highly identical schedules; do not conflate feeds with different times
# retain channel IDs but attach multiple platforms on merged entries when identical
normalized=collections.defaultdict(list)
for c in channels:
 key=re.sub(r'\s+(hd|sd|4k)$','',c['name'].strip().casefold())
 key=re.sub(r'[^\wα-ωά-ώ]+','',key)
 normalized[key].append(c)
removed=set();merged_count=0
for key,cs in normalized.items():
 for i,c in enumerate(cs):
  if c['id'] in removed:continue
  a={(x[0],x[1],x[2].casefold()) for x in c['events'] if x[0]<1440 and x[1]>0}
  for d in cs[i+1:]:
   if d['id'] in removed:continue
   b={(x[0],x[1],x[2].casefold()) for x in d['events'] if x[0]<1440 and x[1]>0}
   if a and b and len(a&b)/max(1,min(len(a),len(b)))>=.93 and abs(len(a)-len(b))<=2:
    if len(d['events'])>len(c['events']):c['events']=d['events']
    c.setdefault('merged',[]).append(d['name']+' · '+d['country'])
    removed.add(d['id']);merged_count+=1
channels=[c for c in channels if c['id'] not in removed]
# compact arrays, icon omitted for privacy/external dependencies
payload=[[c['id'],c['name'],c['country'],c['provider'],c['type'],c['events'],c.get('merged',[])] for c in channels]
raw=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('</','<\\/')
print('channels:',len(channels),'auto merged:',merged_count,'events:',sum(len(c['events']) for c in channels),'payload MB:',round(len(raw.encode())/1e6,2))
PAGE=r'''<!doctype html><html lang="el"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>EPG Ελλάδας & Κύπρου | XMLTV</title>
<style>
:root{font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif;color-scheme:dark;background:#0b1220;color:#e9f1fb;--bg:#111e30;--panel:#17253b;--line:#35445b;--muted:#9ab0c9;--accent:#54c5e2}
*{box-sizing:border-box}body{margin:0;padding:16px;max-width:1800px;margin-inline:auto}h1{font-size:clamp(20px,3vw,30px);margin:0 0 4px}.small{font-size:12px;color:var(--muted)}.toolbar{display:flex;flex-wrap:wrap;gap:9px;align-items:center;margin:16px 0}.tool{background:var(--panel);color:inherit;border:1px solid var(--line);border-radius:9px;padding:9px 11px;font-size:13px;max-width:100%}select,button,input{font:inherit}button{cursor:pointer}button:hover{border-color:var(--accent)}input{min-width:130px}.tabs{display:flex;gap:5px;flex-wrap:wrap}.tabs button{border:1px solid var(--line);color:inherit;background:var(--bg);border-radius:8px;padding:8px 10px;font-size:12px}.tabs button.active{background:#13516b;border-color:#56bed5}.metrics{display:flex;flex-wrap:wrap;gap:10px;color:var(--muted);font-size:12px;padding:8px 0}.board{border:1px solid var(--line);border-radius:12px;overflow:auto;height:min(67vh,760px);position:relative;background:var(--bg)}.wide{width:calc(190px + 2640px);position:relative}.timeline-head{display:flex;position:sticky;top:0;z-index:10;background:#17283e;height:55px;border-bottom:1px solid var(--line)}.station{width:190px;flex:none;position:sticky;left:0;z-index:3;background:#14243a;border-right:1px solid var(--line);padding:9px 11px;display:flex;flex-direction:column;justify-content:center;gap:4px}.timeline-head .station{z-index:12}.station strong{font-size:12px;max-width:170px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.station small{font-size:10px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.hours{display:flex;width:2640px;flex:none;position:relative}.hour{width:110px;flex:none;padding:13px 6px;color:#c6d6e8;font-size:12px;border-left:1px solid var(--line)}.end-mark{position:absolute;left:2537px;top:4px;background:#22445b;border-radius:5px;padding:4px 7px;font-size:11px;white-space:nowrap;color:#f4fbff}.row{display:flex;height:62px;border-bottom:1px solid #2c3b50}.track{flex:none;width:2640px;position:relative;background:repeating-linear-gradient(90deg,transparent 0,transparent 109px,#28384f 109px,#28384f 110px)}.event{position:absolute;top:6px;height:49px;padding:5px 7px;border-radius:5px;border:1px solid #5192b6;background:#1c4868;color:#edf8ff;text-align:left;overflow:hidden;font-size:11px}.event:nth-of-type(2n){background:#215c54;border-color:#4a9a83}.event.film{background:#643750;border-color:#ae7089}.event.doc{background:#205e4e;border-color:#499e83}.event.sport{background:#513b76;border-color:#8b70b9}.event.kids{background:#64521a;border-color:#bba14c}.event.music{background:#58436a;border-color:#ae87d1}.event.news{background:#60502e;border-color:#aa9062}.event strong{font-size:11px;display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.event small{display:block;font-size:10px;opacity:.8;margin-top:3px;white-space:nowrap}.void{color:#718aa8;font-size:11px;position:absolute;left:10px;top:21px}.card{background:var(--panel);border:1px solid var(--line);border-radius:11px;padding:12px 15px;margin-top:12px;min-height:90px}.card a{color:#74daf4}.legend{display:flex;flex-wrap:wrap;gap:12px;margin:12px 0;font-size:12px;color:var(--muted)}.swatch{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}.footer{font-size:12px;color:var(--muted);margin-top:12px;line-height:1.55}.status{color:#9fe0ad}.err{color:#ffb0a7}@media(max-width:620px){body{padding:9px}.toolbar{gap:6px}.station{width:155px}.wide{width:2795px}.board{height:68vh}.tool{font-size:12px;padding:8px}.station strong{font-size:11px}} 
</style></head><body><h1>📺 EPG Ελλάδας & Κύπρου</h1>
<div class="small">Αυτόματα ανανεούμενος οδηγός από EPGShare01 GR1 και CY1 · πραγματικοί τίτλοι, ώρες έναρξης και λήξης · ζώνη ώρας Europe/Athens</div>
<div class="toolbar">
<label>Ημέρα <select id="day" class="tool">__DAY_OPTIONS__</select></label>
<label>Περιοχή <select id="country" class="tool"><option value="all">Ελλάδα & Κύπρος</option><option value="GR">Ελλάδα</option><option value="CY">Κύπρος</option></select></label>
<label>Πάροχος / ομάδα <select id="provider" class="tool"><option value="all">Όλα</option><option value="MAGENTA">MAGENTA</option><option value="NOVA">Nova/EON</option><option value="ANT1+">ANT1+</option><option value="CYTAVISION">Cytavision</option><option value="CABLENET">Cablenet</option><option value="GR">Λοιπά Ελλάδας</option><option value="CY">Λοιπά Κύπρου</option></select></label>
<label>Είδος <select id="genre" class="tool"><option value="all">Όλα τα είδη</option><option value="film">Ταινίες</option><option value="series">Σειρές</option><option value="doc">Ντοκιμαντέρ</option><option value="kids">Παιδικά</option><option value="sport">Αθλητικά</option><option value="news">Ειδήσεις</option><option value="music">Μουσική</option><option value="general">Γενικά</option></select></label>
<input id="query" class="tool" type="search" placeholder="Αναζήτηση καναλιού..." aria-label="Αναζήτηση καναλιού">
<label class="small"><input type="checkbox" id="hideempty" checked> Μόνο με πρόγραμμα</label>
</div>
<div class="toolbar"><div class="tabs"><button data-hour="0">00:00</button><button data-hour="6">06:00</button><button data-hour="12" class="active">12:00</button><button data-hour="18">18:00</button><button data-hour="21">21:00</button><button data-hour="24">Αύριο 00:00</button></div><button id="prev" class="tool">←</button><button id="next" class="tool">→</button></div>
<div class="metrics"><span id="count"></span><span id="range"></span><span id="loaded" class="status"></span></div>
<div class="board" id="board" tabindex="0"><div class="wide"><div class="timeline-head"><div class="station"><strong>Κανάλι</strong><small id="leftDate">Ημερομηνία</small></div><div class="hours" id="hours"></div></div><div id="rows"></div></div></div>
<div class="card" id="detail"><strong>Πάτησε μία εκπομπή.</strong><p class="small">Θα εμφανιστούν ώρα έναρξης, ώρα λήξης και περιγραφή, όπως περιέχονται στο αρχείο XMLTV.</p></div>
<div class="legend"><span><i class="swatch" style="background:#643750"></i>Ταινίες</span><span><i class="swatch" style="background:#205e4e"></i>Ντοκιμαντέρ</span><span><i class="swatch" style="background:#513b76"></i>Αθλητικά</span><span><i class="swatch" style="background:#64521a"></i>Παιδικά</span><span><i class="swatch" style="background:#58436a"></i>Μουσική</span><span><i class="swatch" style="background:#60502e"></i>Ειδήσεις</span></div>
<div class="footer">Πηγή: τα τοπικά αντίγραφα EPGShare01 GR1 / CY1 που ανέβασες. Τα δεδομένα ενσωματώνονται στο HTML κατά την τελευταία επιτυχή ενημέρωση. Οι ώρες είναι μετατρεμμένες στη ζώνη Ελλάδας/Κύπρου και τα δεδομένα αφορούν τις 8–10 Νοεμβρίου 2026· για επόμενες ημέρες χρειάζονται νέα XMLTV. Φίλτρο παρόχου: ασφαλής κατηγοριοποίηση από την ονομασία καναλιού, όχι πιστοποιημένη λίστα δικαιωμάτων συνδρομής. Ομοειδή ονόματα με διαφορετικό πρόγραμμα διατηρούνται χωριστά, γιατί ενδέχεται να είναι διαφορετικές ροές.</div>
<script>const DATA=__DATA__;
const base=__BASE__;
const DAY_OFFSETS=__DAY_OFFSETS__;
const $=id=>document.getElementById(id),clamp=(x,a,b)=>Math.min(b,Math.max(a,x));
const fmtTime=min=>{let d=new Date((base+min)*60000);return new Intl.DateTimeFormat('el-GR',{timeZone:'Europe/Athens',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(d)};
const fmtDate=min=>new Intl.DateTimeFormat('el-GR',{timeZone:'Europe/Athens',day:'2-digit',month:'2-digit',year:'numeric'}).format(new Date((base+min)*60000));
let dateIndex=0,visible=[];
function show(e,c){const [a,b,title,desc,cat]=e;const node=$('detail');node.replaceChildren();const h=document.createElement('strong');h.textContent=title||'(Χωρίς τίτλο)';const line=document.createElement('p');line.textContent=c[1]+' · '+fmtDate(a)+' '+fmtTime(a)+' – '+fmtDate(b)+' '+fmtTime(b);const d=document.createElement('p');d.className='small';d.textContent=desc||'Δεν υπάρχει περιγραφή στο XMLTV.';const badge=document.createElement('p');badge.className='small';badge.textContent='Πηγή: XMLTV '+c[2]+' · '+c[0]+(cat?' · '+cat:'');node.append(h,line,d,badge)}
function render(){const start=DAY_OFFSETS[dateIndex],end=DAY_OFFSETS[dateIndex+1];const country=$('country').value,p=$('provider').value,genre=$('genre').value,q=$('query').value.toLocaleLowerCase('el'),hide=$('hideempty').checked;
visible=DATA.filter(c=>(country==='all'||c[2]===country)&&(p==='all'||c[3]===p)&&(genre==='all'||c[4]===genre)&&(!q||(c[1]+' '+c[0]).toLocaleLowerCase('el').includes(q))&&(!hide||c[5].some(e=>e[0]<end&&e[1]>start)));
const holder=$('rows');holder.replaceChildren();let evcount=0,fully=0;const fragment=document.createDocumentFragment();
for(const c of visible){const matches=c[5].filter(e=>e[0]<end&&e[1]>start);evcount+=matches.length;const row=document.createElement('div');row.className='row';const station=document.createElement('div');station.className='station';const name=document.createElement('strong');name.textContent=c[1];name.title=c[0];const sub=document.createElement('small');sub.textContent=c[2]+' · '+(c[3]==='GR'||c[3]==='CY'?'Θεματικό / ελεύθερο':c[3])+(c[6].length?' · '+(c[6].length+1)+' ισοδύναμες εγγραφές':'');station.append(name,sub);const tr=document.createElement('div');tr.className='track';let covered=[];
for(const e of matches){const a=clamp(e[0],start,end),b=clamp(e[1],start,end);if(b<=a)continue;covered.push([a,b]);const btn=document.createElement('button');btn.className='event '+c[4];btn.style.left=((a-start)/1440*2640+1)+'px';btn.style.width=Math.max(3,((b-a)/1440*2640-2))+'px';btn.title=fmtTime(e[0])+'–'+fmtTime(e[1])+' '+e[2];const t=document.createElement('strong');t.textContent=e[2]||'Χωρίς τίτλο';const sm=document.createElement('small');sm.textContent=fmtTime(e[0])+'–'+fmtTime(e[1]);btn.append(t,sm);btn.addEventListener('click',()=>show(e,c));tr.appendChild(btn)}
covered.sort((a,b)=>a[0]-b[0]);let total=0,last=start;for(const [a,b] of covered){total+=Math.max(0,b-Math.max(last,a));last=Math.max(last,b)}if(total>=1400)fully++;
if(!matches.length){const blank=document.createElement('span');blank.className='void';blank.textContent='Δεν υπάρχει πρόγραμμα στο XMLTV για αυτή την ημέρα';tr.appendChild(blank)}row.append(station,tr);fragment.appendChild(row)}holder.appendChild(fragment);
$('count').textContent=visible.length+' κανάλια · '+evcount+' εκπομπές · '+fully+' με ≥23ω20λ κάλυψη';$('range').textContent=fmtDate(start)+' 00:00 → '+fmtDate(end)+' 00:00';$('leftDate').textContent=fmtDate(start)+' 00:00';
const hours=$('hours');hours.replaceChildren();for(let i=0;i<24;i++){let el=document.createElement('div');el.className='hour';el.textContent=String(i).padStart(2,'0')+':00';hours.appendChild(el)}let lab=document.createElement('div');lab.className='end-mark';lab.textContent=fmtDate(end)+' 00:00';hours.appendChild(lab);
}
function jump(hour){const v=$('board');v.scrollTo({left:Math.max(0,190+hour*110-v.clientWidth*.28),behavior:'smooth'});document.querySelectorAll('[data-hour]').forEach(b=>b.classList.toggle('active',Number(b.dataset.hour)===hour))}
for(const id of ['country','provider','genre','hideempty','day'])$(id).addEventListener('change',()=>{dateIndex=Number($('day').value);render()});$('query').addEventListener('input',render);document.querySelectorAll('[data-hour]').forEach(b=>b.addEventListener('click',()=>jump(Number(b.dataset.hour))));$('prev').addEventListener('click',()=>$('board').scrollBy({left:-400,behavior:'smooth'}));$('next').addEventListener('click',()=>$('board').scrollBy({left:400,behavior:'smooth'}));$('loaded').textContent='XMLTV ενσωματωμένο — δεν απαιτείται φόρτωση αρχείων';render();requestAnimationFrame(()=>jump(12));
</script></body></html>'''
out=str(Path(__file__).parent/'site'/'index.html')
day_names=['Δευτέρα','Τρίτη','Τετάρτη','Πέμπτη','Παρασκευή','Σάββατο','Κυριακή']
opts=''.join('<option value=\"%s\">%s %s</option>'%(i,day_names[(start+datetime.timedelta(days=i)).weekday()],(start+datetime.timedelta(days=i)).strftime('%d/%m/%Y')) for i in range(3))
offsets=[int(((start+datetime.timedelta(days=i)).timestamp()//60)-start_ts) for i in range(4)]
PAGE=PAGE.replace('__DAY_OPTIONS__',opts).replace('__DAY_OFFSETS__',json.dumps(offsets)).replace('__BASE__',str(start_ts)).replace('__DATA__',raw)
with open(out,'w',encoding='utf-8') as f:f.write(PAGE)
print('Output',out,os.path.getsize(out))
