declare module 'winbox' {
  export interface WinBoxSettings {
    title: string;
    width: number | string;
    height: number | string;
    x: number | string;
    y: number | string;
    background: string;
    mount?: HTMLElement;
    url?: string;
    html?: string;
    class?: string;
  }

  export default class WinBox {
    constructor(title: string, options?: Partial<WinBoxSettings>);
    body: HTMLElement;
    onclose?: () => boolean | void;
    close(): void;
    focus(): void;
    hide(): void;
    show(): void;
    setTitle(title: string): void;
    resize(width: number | string, height: number | string): void;
    move(x: number | string, y: number | string): void;
  }
}

declare module 'winbox/src/js/winbox' {
  import WinBox from 'winbox';
  export default WinBox;
}
