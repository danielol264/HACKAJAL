import { useEffect, useState } from 'react';
import { Navbar, Footer } from './components/Layout';
import { BackButton } from './components/UI';
import { Home, Alerts, Prevention, Articles, Survey, About } from './pages/Pages';

const views = { inicio: Home, alertas: Alerts, prevencion: Prevention, articulos: Articles, encuesta: Survey, acerca: About };
const routeFromUrl = () => {
  const route = window.location.hash.replace('#/', '') || 'inicio';
  return views[route] ? route : 'inicio';
};

export default function App() {
  const [p, setP] = useState(routeFromUrl);
  const [open, setOpen] = useState(false);
  const Page = views[p];

  useEffect(() => {
    const sync = () => setP(routeFromUrl());
    window.addEventListener('popstate', sync);
    window.addEventListener('hashchange', sync);
    return () => {
      window.removeEventListener('popstate', sync);
      window.removeEventListener('hashchange', sync);
    };
  }, []);

  const go = (x, { replace = false } = {}) => {
    if (!views[x]) return;
    const url = `#/${x}`;
    if (replace) window.history.replaceState({ hackajal: true, route: x }, '', url);
    else if (routeFromUrl() !== x) window.history.pushState({ hackajal: true, route: x, from: p }, '', url);
    setP(x);
    setOpen(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const back = () => {
    if (window.history.state?.hackajal && window.history.state.from) {
      window.history.back();
      return;
    }
    go('inicio', { replace: true });
  };

  return (
    <>
      <Navbar page={p} go={go} open={open} setOpen={setOpen} />
      <main>
        {p !== 'inicio' && <div className="back-wrap"><BackButton onClick={back} /></div>}
        <Page go={go} />
      </main>
      <Footer go={go} />
    </>
  );
}
