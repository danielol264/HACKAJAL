import { useState } from 'react';
import { Sidebar, Header } from './components/Layout';
import { Dashboard, Dengue, Cronicas, Territorio, Fuentes, Prevencion, Acerca } from './pages/Pages';
const views={inicio:Dashboard,dengue:Dengue,cronicas:Cronicas,territorio:Territorio,fuentes:Fuentes,prevencion:Prevencion,acerca:Acerca}; const names={inicio:'Inicio',dengue:'Vigilancia de dengue',cronicas:'Enfermedades crónicas',territorio:'Información territorial',fuentes:'Fuentes de datos',prevencion:'Información preventiva',acerca:'Acerca del proyecto'};
export default function App(){const [page,setPage]=useState('inicio');const [open,setOpen]=useState(false);const Page=views[page];return <div className="app"><Sidebar page={page} setPage={setPage} open={open} close={()=>setOpen(false)}/><main><Header title={names[page]} toggle={()=>setOpen(true)}/><div className="content"><Page/></div></main></div>}
