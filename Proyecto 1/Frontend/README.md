# SmartEgg — Frontend

Panel web para monitorear en tiempo real la incubadora inteligente SmartEgg
(temperatura, humedad, alarmas, lotes de huevos) a partir de los datos que el
Arduino envía al backend Flask.

## Stack

- [Vite](https://vite.dev/) + React (JavaScript, sin TypeScript)
- [Tailwind CSS v4](https://tailwindcss.com/)
- [React Router](https://reactrouter.com/) — navegación entre vistas
- [Recharts](https://recharts.org/) — gráficas de temperatura/humedad
- [lucide-react](https://lucide.dev/) — iconografía
- [react-hot-toast](https://react-hot-toast.com/) — notificaciones de alarmas

## Vistas

- **Panel en vivo** (`/`) — lectura actual (temperatura, humedad, sistema,
  espacios libres), gauges con rango seguro y gráfica en tiempo real vía
  Server-Sent Events (`/api/sensores/stream`).
- **Historial** (`/historial`) — tabla de lecturas guardadas en MongoDB.
- **Alarmas** (`/alarmas`) — condiciones críticas detectadas.
- **Lotes** (`/lotes`) — CRUD de lotes de incubación.
- **Reportes** (`/reportes`) — descarga de reporte PDF.

## Configuración

Crea un `.env` (o copia `.env.example`) con la URL del backend Flask:

```
VITE_API_BASE_URL=http://localhost:5000
```

## Desarrollo

```bash
npm install
npm run dev
```

Requiere que el backend (`../Backend`) esté corriendo y accesible desde
`VITE_API_BASE_URL`, con CORS habilitado para `/api/*` (ya viene configurado
en el backend).

## Build de producción

```bash
npm run build
npm run preview
```
