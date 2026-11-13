// Único punto de integración futura con Django REST Framework.
// Mientras VITE_API_URL no exista o el backend no responda, la interfaz usa datos DEMO.
const baseUrl=import.meta.env.VITE_API_URL||'';
async function get(path){
  if(!baseUrl)return null;
  const response=await fetch(`${baseUrl}${path}`);
  if(!response.ok)throw new Error(`API error: ${response.status}`);
  return response.json();
}
export const api={municipalities:()=>get('/api/municipios/'),municipality:id=>get(`/api/municipios/${id}/`),risks:()=>get('/api/riesgos/'),history:()=>get('/api/historicos/'),alerts:()=>get('/api/alertas/'),recommendations:()=>get('/api/recomendaciones/'),healthCenters:()=>get('/api/centros-salud/')};
