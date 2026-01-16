# HORNET Dashboard Integration Guide

## Files Included

```
hornet-dashboard/
├── hornet-logo-transparent.png     # Full-size logo (transparent)
├── hornet-logo-512x512.png         # Large (hero sections)
├── hornet-logo-256x256.png         # Medium (headers)
├── hornet-logo-128x128.png         # Small (nav)
├── hornet-logo-64x64.png           # Icon
├── hornet-logo-32x32.png           # Favicon
├── hornet-logo-16x16.png           # Tiny favicon
├── hornet-benchmarks-final.jsx     # Interactive benchmarks page
├── hornet-api-hooks.js             # API integration hooks
└── README.md                       # This file
```

## Quick Setup

### 1. Add to your existing HORNET project

```powershell
cd C:\Projects\hornet

# Create frontend directory
mkdir -p dashboard/src/assets
mkdir -p dashboard/src/hooks
mkdir -p dashboard/src/pages
mkdir -p dashboard/public

# Copy the logos
cp hornet-logo-*.png dashboard/public/
cp hornet-logo-transparent.png dashboard/public/hornet-logo-transparent.png
```

### 2. Initialize React project (if not exists)

```powershell
cd dashboard
npm create vite@latest . -- --template react
npm install
npm install framer-motion lucide-react
```

### 3. Add Tailwind CSS

```powershell
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p
```

Update `tailwind.config.js`:
```javascript
/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        slate: {
          950: '#0a0e14',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        display: ['Space Grotesk', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
```

Update `src/index.css`:
```css
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Space+Grotesk:wght@400;500;600;700&display=swap');
@tailwind base;
@tailwind components;
@tailwind utilities;
```

### 4. Environment Variables

Create `dashboard/.env`:
```env
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

### 5. File Structure

```
dashboard/
├── public/
│   ├── hornet-logo-transparent.png
│   ├── hornet-logo-32x32.png (favicon)
│   └── index.html
├── src/
│   ├── assets/
│   ├── hooks/
│   │   └── useHornetApi.js         # Copy hornet-api-hooks.js here
│   ├── pages/
│   │   ├── Benchmarks.jsx          # Copy hornet-benchmarks-final.jsx here
│   │   ├── Dashboard.jsx           # Main dashboard
│   │   ├── Landing.jsx             # Marketing landing
│   │   └── Login.jsx               # Auth page
│   ├── components/
│   │   ├── HornetLogo.jsx
│   │   ├── IncidentTable.jsx
│   │   ├── StatsCard.jsx
│   │   └── ...
│   ├── App.jsx
│   ├── main.jsx
│   └── index.css
├── .env
├── package.json
├── tailwind.config.js
└── vite.config.js
```

## Using the API Hooks

```jsx
import { useIncidents, useStats, useWebSocket, useHealth } from './hooks/useHornetApi';

function Dashboard() {
  const { incidents, loading, error, refetch } = useIncidents({ 
    state: null, 
    limit: 50,
    autoRefresh: 5000 
  });
  
  const stats = useStats();
  const { health } = useHealth();
  
  // Real-time updates
  useWebSocket((message) => {
    console.log('New incident update:', message);
    refetch();
  });

  return (
    <div>
      <StatsBar stats={stats} />
      <IncidentTable incidents={incidents} />
      <SystemHealth health={health} />
    </div>
  );
}
```

## Docker Integration

Add to your `docker-compose.yml`:

```yaml
services:
  # ... existing services ...
  
  dashboard:
    build:
      context: ./dashboard
      dockerfile: Dockerfile
    ports:
      - "3000:80"
    environment:
      - VITE_API_URL=http://api:8000
      - VITE_WS_URL=ws://api:8000
    depends_on:
      - api
```

Create `dashboard/Dockerfile`:
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Create `dashboard/nginx.conf`:
```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
    
    location /ws {
        proxy_pass http://api:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
    }
}
```

## Key Features

### Benchmarks Page (`/benchmarks`)
- **Speed Race**: Interactive comparison of HORNET vs human SOC response times
- **Savings Calculator**: ROI calculator with sliders for team size and incident volume
- **Accuracy Gauge**: 79.9% auto-resolution visualization with Scavenger Logic demo
- **Consensus Depth**: Watch 12 agents deliberate on a critical incident
- **Compliance Dashboard**: HIPAA/GDPR/PCI assessment tracking with audit trails

### Customer-Focused Messaging
- All metrics framed as **customer savings**, not internal costs
- ROI calculated as: `(Current Team Cost) - (1 Analyst + HORNET) = Annual Savings`
- Time savings shown as "analyst hours reclaimed"
- Compliance shown as "audit prep time eliminated"

## Logo Usage

| Size | Use Case |
|------|----------|
| transparent.png | Hero sections, large displays |
| 512x512 | Marketing materials |
| 256x256 | Dashboard headers |
| 128x128 | Navigation |
| 64x64 | App icons |
| 32x32 | Favicon, small UI |
| 16x16 | Tiny favicon |

## Next Steps

1. [ ] Copy files to `C:\Projects\hornet\dashboard`
2. [ ] Run `npm install`
3. [ ] Update `.env` with your API URL
4. [ ] Run `npm run dev` to test
5. [ ] Add to docker-compose.yml
6. [ ] Push to GitHub

## API Endpoints Used

From your `hornet/api/routes/incidents.py`:

| Endpoint | Hook | Usage |
|----------|------|-------|
| `GET /api/v1/incidents` | `useIncidents` | Main incident list |
| `GET /api/v1/incidents/{id}` | `useIncident` | Incident details + findings |
| `GET /api/v1/incidents/findings/recent` | `useRecentFindings` | Sidebar feed |
| `POST /api/v1/incidents/{id}/action` | `useIncidentAction` | APPROVE/REJECT/MODIFY |
| `GET /api/v1/health` | `useHealth` | System status |
| `WS /ws/incidents` | `useWebSocket` | Real-time updates |

---

Built for HORNET Autonomous SOC 🐝
