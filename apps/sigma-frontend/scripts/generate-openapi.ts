import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import openapiTS from 'openapi-typescript';

const CURRENT_PATH = path.dirname(fileURLToPath(import.meta.url));
const PROJECT_ROOT = path.resolve(CURRENT_PATH, '..');
const OUTPUT_PATH = path.join(PROJECT_ROOT, 'src/api/generated.ts');

const SPEC_PATH = process.env.OPENAPI_SPEC_PATH;

if (!SPEC_PATH) {
  throw new Error('Set OPENAPI_SPEC_PATH to the FastAPI OpenAPI document before running generate:api.');
}

const schema = await openapiTS(SPEC_PATH, {
  alphabetize: true
});

fs.mkdirSync(path.dirname(OUTPUT_PATH), { recursive: true });
fs.writeFileSync(
  OUTPUT_PATH,
  ['// Generated from FastAPI OpenAPI schema. Do not edit by hand.', schema].join('\n'),
  'utf8'
);

const typesPath = path.join(PROJECT_ROOT, 'src/api/types.ts');

if (!fs.existsSync(typesPath)) {
  fs.writeFileSync(
    typesPath,
    [
      '// Shared API surface types belong here.',
      '// Extend this file with hand-authored types that augment the generated contract.'
    ].join('\n'),
    'utf8'
  );
}
