export interface BlueprintDimensions {
  width: number | string;
  height: number | string;
}

export interface BlueprintPosition {
  x: number | 'center';
  y: number | 'center';
}

export interface WindowBlueprint {
  id: string;
  title: string;
  component: string;
  description?: string;
  dimensions: BlueprintDimensions;
  position: BlueprintPosition;
}

export type BlueprintCatalog = WindowBlueprint[];
