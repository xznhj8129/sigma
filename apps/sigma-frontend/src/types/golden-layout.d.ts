declare module 'golden-layout' {
  export interface GoldenLayoutItemConfig {
    type: string;
    componentName?: string;
    componentState?: Record<string, unknown>;
    content?: GoldenLayoutItemConfig[];
    isClosable?: boolean;
    title?: string;
  }

  export interface GoldenLayoutConfig {
    settings?: Record<string, unknown>;
    content: GoldenLayoutItemConfig[];
    dimensions?: Record<string, number>;
    labels?: Record<string, string>;
  }

  export interface ContentItem {
    container: Container;
  }

  export interface Container {
    getElement(): HTMLElement | unknown;
    setTitle(title: string): void;
  }

  export default class GoldenLayout {
    constructor(config: GoldenLayoutConfig, container?: HTMLElement);
    registerComponent(
      name: string,
      callback: (container: Container, state: Record<string, unknown>) => void
    ): void;
    init(): void;
    destroy(): void;
    updateSize(width?: number, height?: number): void;
  }
}
