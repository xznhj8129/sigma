# Sigma Frontend (React + Vite)

React rewrite of the legacy Flask templates. GoldenLayout and WinBox recreate the desktop-style workspace and windowed modules, while FastAPI/OpenAPI and YAML blueprints feed typed contracts into the UI.

## Getting started

```bash
cd apps/sigma-frontend
npm install
npm run dev
```

## API contract generation

```bash
export OPENAPI_SPEC_PATH=/absolute/path/to/openapi.json
npm run generate:api
```

The output lands in `src/api/generated.ts`; the script refuses to run when the environment variable is missing.

## Blueprint generation

Blueprint sources live in `blueprints/*.yaml`. Regenerate the TypeScript catalog after edits:

```bash
npm run generate:blueprints
```

The catalog is written to `src/blueprints/generated.ts` and consumed by the Workspace Start menu.
