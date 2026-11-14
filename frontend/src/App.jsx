import { useEffect, useState } from 'react';
import { Navbar, Footer } from './components/Layout';
import { BackButton } from './components/UI';
import Home from './pages/Home';
import Alerts from './pages/Alerts';
import HealthInfo from './pages/HealthInfo';
import ContentDetail from './pages/ContentDetail';
import Survey from './pages/Survey';
import {
  Epidemiology,
  Municipality,
  RiskMap,
  History,
  HealthCenters,
  About,
} from './pages/Pages';

const views = {
  inicio: Home,
  alertas: Alerts,
  prevencion: HealthInfo,
  contenidos: ContentDetail,
  encuesta: Survey,
  situacion: Epidemiology,
  municipios: Municipality,
  mapa: RiskMap,
  historial: History,
  centros: HealthCenters,
  acerca: About,
};

function parseUrl() {
  const hash = window.location.hash.replace(/^#\/?/, '');
  const [pathPart, queryPart] = hash.split('?');
  const segments = pathPart.split('/').filter(Boolean);
  const route = segments[0] || 'inicio';

  let id = segments[1] || null;
  if (!id && queryPart) {
    const params = new URLSearchParams(queryPart);
    id = params.get('id');
  }

  return {
    route: views[route] ? route : 'inicio',
    id,
  };
}

export default function App() {
  const [current, setCurrent] = useState(parseUrl);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handleUrlChange = () => {
      setCurrent(parseUrl());
    };
    window.addEventListener('popstate', handleUrlChange);
    window.addEventListener('hashchange', handleUrlChange);
    return () => {
      window.removeEventListener('popstate', handleUrlChange);
      window.removeEventListener('hashchange', handleUrlChange);
    };
  }, []);

  const go = (targetRoute, { id = null, replace = false } = {}) => {
    if (!views[targetRoute]) return;

    let newHash = `#/${targetRoute}`;
    if (id !== null && id !== undefined) {
      newHash = `#/${targetRoute}/${id}`;
    }

    if (replace) {
      window.history.replaceState({ hackajal: true, route: targetRoute, id }, '', newHash);
    } else {
      window.history.pushState({ hackajal: true, route: targetRoute, id, from: current.route }, '', newHash);
    }

    setCurrent({ route: targetRoute, id });
    setOpen(false);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const back = () => {
    const state = window.history.state;
    if (state?.hackajal && state.from) {
      window.history.back();
      return;
    }
    go('inicio', { replace: true });
  };

  const Page = views[current.route] || Home;

  return (
    <>
      <Navbar page={current.route} go={go} open={open} setOpen={setOpen} />
      <main>
        {current.route !== 'inicio' && (
          <div className="back-wrap">
            <BackButton onClick={back} />
          </div>
        )}
        <Page go={go} id={current.id} />
      </main>
      <Footer go={go} />
    </>
  );
}
