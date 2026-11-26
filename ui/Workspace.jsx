import React,{useEffect,useState} from 'react'
import './style.css'

const titles={partner:'Управление нодами',seller:'Отправления продавца',drive:'Перевозки водителя',node:'Приём и выдача',fleet:'Транспорт и расписание',wild:'Тарифы Wild',atlas:'Планирование Atlas'}
function quantity(value) {
 return Number(value).toLocaleString('ru-RU',{maximumFractionDigits:3})
}
function token(){return document.cookie.split('; ').find(c=>c.startsWith('csrftoken='))?.slice(10)}
function Entry({spec,act,busy,preview}){
 return <section><h2>{spec.label}</h2><form onSubmit={e=>{e.preventDefault();const form=e.currentTarget;const data=Object.fromEntries(new FormData(form));act(e.nativeEvent.submitter.value,data)}}>
 {spec.fields.map(f=><label key={f.name}>{f.label}{f.type==='select'?<select name={f.name} required={f.required} defaultValue=""><option value="">Выберите</option>{f.options.map(([id,text])=><option key={id} value={id}>{text}</option>)}</select>:<input name={f.name} required={f.required} type={f.type} step="any"/>}</label>)}
 {preview && <button disabled={busy} value="quote">Рассчитать</button>}<button disabled={busy} value={spec.action}>{spec.label}</button></form></section>
}

export function Workspace({service}){
 const [view,setView]=useState({}),[error,setError]=useState(''),[result,setResult]=useState(null),[busy,setBusy]=useState(false)
 async function load(){const response=await fetch('/api/');const body=await response.json();if(!response.ok)throw Error(body.error);setView(body)}
 async function refresh(){try{setError('');await load()}catch(e){setError(e.message)}}
 useEffect(()=>{refresh()},[])
 async function act(action,data){
  setBusy(true);setError('');setResult(null)
  try{const r=await fetch('/api/',{method:'POST',headers:{'Content-Type':'application/json','X-CSRFToken':token()},body:JSON.stringify({action,data})})
   if(!r.headers.get('Content-Type')?.includes('json'))throw Error('Сессия истекла. Обновите страницу.')
   const b=await r.json();if(!r.ok)throw Error(b.error);setResult(b.result||'Сохранено');await load()
  }catch(e){setError(e.message)}finally{setBusy(false)}
 }
 return <><header><b>WB <i>Wine</i></b><span>{service.toUpperCase()}</span><span>{view.username}</span><form method="post" action="/logout/"><input type="hidden" name="csrfmiddlewaretoken" value={token()||''}/><button>Выйти</button></form></header><main><div className="heading"><h1>{titles[service]}</h1><button onClick={refresh}>Обновить</button></div>
 {error&&<p role="alert">{error}</p>}{typeof result==='string'&&<p role="status">{result}</p>}{result?.cost&&<section><h2>{result.route.join(' → ')}</h2><p>Хранение <b>{Number(result.cost.berries).toLocaleString("ru-RU",{maximumFractionDigits:3})} Berry</b> · {result.cost.storage} ₽ за {quantity(result.litres)} л</p><p>Полная стоимость <b>{result.cost.total} ₽</b></p><p>Перевозка {result.cost.transport} ₽ · хранение {result.cost.storage} ₽ · обработка {result.cost.handling} ₽ · риск {result.cost.risk} ₽</p><p>Через РЦ: {result.hub_total?result.hub_total+' ₽':'доступного маршрута нет'}</p></section>}
 {view.cities&&<section><h2>Дороги виртуальной России</h2><svg viewBox="0 0 760 150" role="img" aria-label="Схема городов и дорог">{(()=>{const xy=c=>[(view.cities[c][1]-37)*55+20,(57-view.cities[c][0])*85+15];return <>{view.roads.map(([a,b])=><line key={a+b} x1={xy(a)[0]} y1={xy(a)[1]} x2={xy(b)[0]} y2={xy(b)[1]} stroke="#987fa5"/>)}{Object.keys(view.cities).map(c=><g key={c} transform={'translate('+xy(c).join(' ')+')'}><circle r="4" fill="#612c71"/><text y="-7" textAnchor="middle" fontSize="12">{c}</text></g>)}</>})()}</svg></section>}
 {result?.rows&&<section><h2>План перевозок · {result.work} ед·км</h2><p>{result.method==='ai'?'Приближённый план ИИ':'Симплексный оптимум'}</p>{result.rows.map(([path,count,km])=><p key={path}>{path} · {count} ед. × {km} км</p>)}</section>}
 {result?.roads?.map((r,i)=><p key={i}>{r?r[1].join(' → ')+' · '+r[0]+' км':'Город плеча ещё не указан'}</p>)}
 {view.tables?.map(t=><section key={t.title}><h2>{t.title}</h2>{!t.rows.length?<p>Записей пока нет.</p>:<div className="scroll"><table><thead><tr>{t.columns.map(c=><th key={c}>{c}</th>)}</tr></thead><tbody>{t.rows.map((r,i)=><tr key={i}>{r.map((v,j)=><td key={j}>{typeof v==='string' && /^\d{4}-\d{2}-\d{2}T/.test(v)?new Date(v).toLocaleString('ru-RU',{timeZone:'Europe/Moscow'}):(t.columns[j].endsWith(', л') || t.columns[j].endsWith(', Berry')) && Number.isFinite(Number(v))?quantity(v):String(v)}</td>)}</tr>)}</tbody></table></div>}</section>)}
 {view.buttons?.map(b=><button disabled={busy} key={b.action+b.id} onClick={()=>act(b.action,{id:b.id})}>{b.label}</button>)}
 {view.forms?.map(spec=><Entry key={spec.action} spec={spec} act={act} busy={busy} preview={service==='seller'}/>)}</main></>
}