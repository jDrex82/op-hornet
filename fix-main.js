const fs = require('fs');
const path = 'C:/Projects/hornet/hornet/main.py';
let content = fs.readFileSync(path, 'utf8');

// Add reports import
content = content.replace(
  'from hornet.api.routes import events, incidents, health, config, webhooks, dashboard, campaigns',
  'from hornet.api.routes import events, incidents, health, config, webhooks, dashboard, campaigns, reports'
);

// Add reports router after incidents router
content = content.replace(
  'app.include_router(incidents.router, prefix="/api/v1/incidents", tags=["Incidents"])',
  `app.include_router(incidents.router, prefix="/api/v1/incidents", tags=["Incidents"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports"])`
);

fs.writeFileSync(path, content);
console.log('main.py updated with reports router!');
