# AXION Gmail Add-on (Phase 4)

## Files
- `Code.gs`: Card Service UI + backend wiring
- `appsscript.json`: Add-on manifest and scopes

## Script Properties required
Set these in Apps Script project settings (`Project Settings -> Script Properties`):
- `AXION_BACKEND_BASE_URL` e.g. `https://your-backend-url.run.app`
- `AXION_INTERNAL_API_KEY` your backend internal key
- `AXION_DEFAULT_EMAIL` fallback email for local/dev tests
- `AXION_DASHBOARD_URL` e.g. `https://your-dashboard-url.run.app`

## Local test behavior
- Sidebar card pulls data from `/api/v1/sidebar/overview`
- `Sync Now` triggers `/api/v1/sidebar/sync`
- Ask AXION uses `/api/v1/sidebar/ask`

## Deploy
1. Create Apps Script project.
2. Copy files from this folder.
3. Configure script properties.
4. Deploy as test add-on and open Gmail developer sandbox.
