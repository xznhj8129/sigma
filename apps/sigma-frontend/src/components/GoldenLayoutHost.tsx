import { useEffect, useRef } from 'react';
import $ from 'jquery';
import type { GoldenLayoutConfig } from 'golden-layout';

type RegisterComponents = (layout: GoldenLayout) => void;

interface GoldenLayoutHostProps {
  config: GoldenLayoutConfig;
  registerComponents: RegisterComponents;
}

const resizeObserverAvailable = typeof ResizeObserver !== 'undefined';

function GoldenLayoutHost({ config, registerComponents }: GoldenLayoutHostProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let layout: import('golden-layout').default | null = null;

    const setup = async () => {
      const containerElement = containerRef.current;

      if (!containerElement) {
        throw new Error('GoldenLayoutHost mounted without a container element.');
      }

      if (typeof window !== 'undefined') {
        (window as unknown as { $: typeof $; jQuery: typeof $ }).$ = $;
        (window as unknown as { $: typeof $; jQuery: typeof $ }).jQuery = $;
      }

      const { default: GoldenLayout } = await import('golden-layout');
      layout = new GoldenLayout(config, containerElement);
      registerComponents(layout);
      layout.init();

      if (resizeObserverAvailable) {
        const observer = new ResizeObserver(() => {
          layout?.updateSize();
        });
        observer.observe(containerElement);
        return () => {
          observer.disconnect();
          layout?.destroy();
        };
      }

      const updateSize = () => {
        layout?.updateSize();
      };

      window.addEventListener('resize', updateSize);

      return () => {
        window.removeEventListener('resize', updateSize);
        layout?.destroy();
      };
    };

    let cleanup: (() => void) | void;

    setup().then((dispose) => {
      cleanup = dispose;
    });

    return () => {
      if (cleanup) {
        cleanup();
      } else if (layout) {
        layout.destroy();
      }
    };
  }, [config, registerComponents]);

  return <div className="gl-container" ref={containerRef} />;
}

export default GoldenLayoutHost;
