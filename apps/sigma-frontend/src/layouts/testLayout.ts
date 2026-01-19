import GoldenLayout, { GoldenLayoutConfig } from 'golden-layout';

export const TEST_GOLDEN_LAYOUT_CONFIG: GoldenLayoutConfig = {
  settings: {
    hasHeaders: false
  },
  content: [
    {
      type: 'row',
      content: [
        {
          type: 'component',
          componentName: 'example',
          componentState: { text: 'Component 1' },
          isClosable: false,
          title: 'Component 1'
        },
        {
          type: 'component',
          componentName: 'example',
          componentState: { text: 'Component 2' },
          isClosable: false,
          title: 'Component 2'
        }
      ]
    }
  ]
};

export const registerTestComponents = (layout: GoldenLayout) => {
  layout.registerComponent('example', function component(container, state) {
    const element = container.getElement() as HTMLElement | { html?: (value: string) => void };
    const content = `<div class="gl-test-pane"><h2>${state.text}</h2></div>`;

    if (element instanceof HTMLElement) {
      element.innerHTML = content;
      return;
    }

    const htmlFn = (element as { html?: (value: string) => void }).html;

    if (typeof htmlFn === 'function') {
      htmlFn.call(element, content);
      return;
    }

    throw new Error('GoldenLayout container does not expose html() or innerHTML.');
  });
};
