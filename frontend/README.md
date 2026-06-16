# SManager Frontend

React + TypeScript + Vite frontend for local SManager monitoring.

## Current Role

- Show forecast products and map overlays.
- Show local MySQL-backed run, FNL, product, and operation metadata.
- Provide a management surface for future server/tunnel actions.

The frontend is not the forecast scheduler. Server-owned scheduling and Slurm submission will be rebuilt in `smanager-server`.

## Start

```bash
cd /Users/wangxu/projects/SManager/frontend
npm install
npm run dev
```

Build:

```bash
npm run build
```
