import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import WinBox from 'winbox/src/js/winbox';
import { blueprintCatalog } from '../blueprints/generated';
import { WindowBlueprint } from '../blueprints/blueprintTypes';
import TestGoldenLayout from '../layouts/TestGoldenLayout';

interface BlueprintPreviewProps {
  blueprint: WindowBlueprint;
}

function BlueprintPreview({ blueprint }: BlueprintPreviewProps) {
  return (
    <div className="window-preview">
      <header>
        <h3>{blueprint.title}</h3>
        {blueprint.description ? <p>{blueprint.description}</p> : null}
      </header>
      <div className="window-placeholder">Module content mounts here.</div>
    </div>
  );
}

const OPEN_WINDOWS: Record<string, WinBox> = {};

function WorkspacePage() {
  const [menuOpen, setMenuOpen] = useState(false);
  const blueprints = blueprintCatalog;

  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest('.start-menu')) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('click', handleClick);
    return () => {
      document.removeEventListener('click', handleClick);
    };
  }, []);

  const handleLaunch = (id: string) => {
    const blueprint = blueprints.find((entry) => entry.id === id);

    if (!blueprint) {
      throw new Error(`Blueprint ${id} does not exist.`);
    }

    const existingWindow = OPEN_WINDOWS[blueprint.id];

    if (existingWindow) {
      existingWindow.focus();
      return;
    }

    const mountNode = document.createElement('div');
    mountNode.classList.add('winbox-mount');
    const root = createRoot(mountNode);
    if (blueprint.component === 'GoldenLayoutTest') {
      root.render(<TestGoldenLayout />);
    } else {
      root.render(<BlueprintPreview blueprint={blueprint} />);
    }

    const winbox = new WinBox(blueprint.title, {
      mount: mountNode,
      width: blueprint.dimensions.width,
      height: blueprint.dimensions.height,
      x: blueprint.position.x,
      y: blueprint.position.y,
      background: '#111827',
      class: 'sigma-winbox'
    });

    OPEN_WINDOWS[blueprint.id] = winbox;
    winbox.onclose = () => {
      root.unmount();
      delete OPEN_WINDOWS[blueprint.id];
    };

    setMenuOpen(false);
  };

  const menuOrder = ['map', 'planner', 'viewer', 'imagery', 'chat', 'test'];
  const menuEntries = menuOrder
    .map((id) => blueprints.find((bp) => bp.id === id))
    .filter((bp): bp is WindowBlueprint => Boolean(bp));

  return (
    <div className="workspace-root">
      <div className="taskbar">
        <div className="start-menu">
          <button className="start-button" onClick={() => setMenuOpen(!menuOpen)} type="button">
            ☰ Start
          </button>
          {menuOpen ? (
            <ul>
              {menuEntries.map((blueprint) => (
                <li key={blueprint.id}>
                  <button type="button" onClick={() => handleLaunch(blueprint.id)}>
                    {blueprint.title}
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      </div>
      <div className="workspace-body" />
    </div>
  );
}

export default WorkspacePage;
