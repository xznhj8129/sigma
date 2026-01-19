import GoldenLayoutHost from '../components/GoldenLayoutHost';
import { registerTestComponents, TEST_GOLDEN_LAYOUT_CONFIG } from './testLayout';

function TestGoldenLayout() {
  return (
    <GoldenLayoutHost
      config={TEST_GOLDEN_LAYOUT_CONFIG}
      registerComponents={registerTestComponents}
    />
  );
}

export default TestGoldenLayout;
