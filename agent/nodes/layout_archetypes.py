import re

ARCHETYPES = [
    {
        "id": "storyboard",
        "name": "Storyboard",
        "keywords": ["story", "narrative", "timeline", "blog", "article", "media", "editorial"],
        "css": """\
.layout-storyboard {
  display: grid;
  grid-template-columns: 1fr;
  grid-template-rows: auto 1fr auto;
  grid-template-areas:
    "header"
    "main"
    "footer";
  min-height: 100vh;
  gap: 0;
}

.layout-storyboard__header { grid-area: header; }
.layout-storyboard__main   { grid-area: main; display: flex; flex-direction: column; gap: 2rem; padding: 2rem; }
.layout-storyboard__footer { grid-area: footer; }

@media (max-width: 768px) {
  .layout-storyboard__main { padding: 1rem; gap: 1rem; }
}""",
        "jsx": """\
export default function StoryboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="layout-storyboard">
      <header className="layout-storyboard__header">{/* header */}</header>
      <main className="layout-storyboard__main">{children}</main>
      <footer className="layout-storyboard__footer">{/* footer */}</footer>
    </div>
  );
}""",
    },
    {
        "id": "operations_console",
        "name": "Operations Console",
        "keywords": ["dashboard", "admin", "console", "monitor", "analytics", "ops", "control"],
        "css": """\
.layout-operations-console {
  display: grid;
  grid-template-columns: 240px 1fr;
  grid-template-rows: 56px 1fr;
  grid-template-areas:
    "sidebar topbar"
    "sidebar content";
  min-height: 100vh;
}

.layout-operations-console__sidebar  { grid-area: sidebar; }
.layout-operations-console__topbar   { grid-area: topbar; }
.layout-operations-console__content  {
  grid-area: content;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
  padding: 1.5rem;
  align-content: start;
}

@media (max-width: 768px) {
  .layout-operations-console {
    grid-template-columns: 1fr;
    grid-template-rows: 56px auto 1fr;
    grid-template-areas:
      "topbar"
      "sidebar"
      "content";
  }
  .layout-operations-console__content { padding: 1rem; gap: 1rem; }
}""",
        "jsx": """\
export default function OperationsConsoleLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="layout-operations-console">
      <aside className="layout-operations-console__sidebar">{/* nav */}</aside>
      <header className="layout-operations-console__topbar">{/* topbar */}</header>
      <main className="layout-operations-console__content">{children}</main>
    </div>
  );
}""",
    },
    {
        "id": "studio",
        "name": "Studio",
        "keywords": ["editor", "studio", "canvas", "create", "design", "builder", "composer"],
        "css": """\
.layout-studio {
  display: grid;
  grid-template-columns: 200px 1fr 280px;
  grid-template-rows: 48px 1fr 36px;
  grid-template-areas:
    "toolbar toolbar toolbar"
    "palette canvas inspector"
    "statusbar statusbar statusbar";
  min-height: 100vh;
}

.layout-studio__toolbar    { grid-area: toolbar; display: flex; align-items: center; gap: 0.5rem; }
.layout-studio__palette    { grid-area: palette; overflow-y: auto; }
.layout-studio__canvas     { grid-area: canvas; overflow: hidden; }
.layout-studio__inspector  { grid-area: inspector; overflow-y: auto; }
.layout-studio__statusbar  { grid-area: statusbar; display: flex; align-items: center; }

@media (max-width: 768px) {
  .layout-studio {
    grid-template-columns: 1fr;
    grid-template-rows: 48px auto 1fr auto 36px;
    grid-template-areas:
      "toolbar"
      "palette"
      "canvas"
      "inspector"
      "statusbar";
  }
}""",
        "jsx": """\
export default function StudioLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="layout-studio">
      <div className="layout-studio__toolbar">{/* tools */}</div>
      <aside className="layout-studio__palette">{/* palette */}</aside>
      <main className="layout-studio__canvas">{children}</main>
      <aside className="layout-studio__inspector">{/* inspector */}</aside>
      <div className="layout-studio__statusbar">{/* status */}</div>
    </div>
  );
}""",
    },
    {
        "id": "atlas",
        "name": "Atlas",
        "keywords": ["map", "atlas", "geo", "location", "spatial", "explore", "navigation"],
        "css": """\
.layout-atlas {
  display: grid;
  grid-template-columns: 360px 1fr;
  grid-template-rows: 56px 1fr;
  grid-template-areas:
    "topbar topbar"
    "panel  map";
  min-height: 100vh;
}

.layout-atlas__topbar { grid-area: topbar; display: flex; align-items: center; }
.layout-atlas__panel  { grid-area: panel; display: flex; flex-direction: column; overflow-y: auto; }
.layout-atlas__map    { grid-area: map; position: relative; }

@media (max-width: 768px) {
  .layout-atlas {
    grid-template-columns: 1fr;
    grid-template-rows: 56px 50vh 1fr;
    grid-template-areas:
      "topbar"
      "map"
      "panel";
  }
}""",
        "jsx": """\
export default function AtlasLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="layout-atlas">
      <header className="layout-atlas__topbar">{/* search / filters */}</header>
      <aside className="layout-atlas__panel">{/* results list */}</aside>
      <main className="layout-atlas__map">{children}</main>
    </div>
  );
}""",
    },
    {
        "id": "notebook",
        "name": "Notebook",
        "keywords": ["notebook", "notes", "document", "wiki", "knowledge", "docs", "write"],
        "css": """\
.layout-notebook {
  display: grid;
  grid-template-columns: 260px 1fr 260px;
  grid-template-rows: 56px 1fr;
  grid-template-areas:
    "topbar  topbar  topbar"
    "outline content toc";
  min-height: 100vh;
}

.layout-notebook__topbar  { grid-area: topbar; }
.layout-notebook__outline { grid-area: outline; overflow-y: auto; }
.layout-notebook__content {
  grid-area: content;
  max-width: 72ch;
  margin: 0 auto;
  padding: 2rem 1.5rem;
  width: 100%;
}
.layout-notebook__toc { grid-area: toc; overflow-y: auto; position: sticky; top: 56px; }

@media (max-width: 768px) {
  .layout-notebook {
    grid-template-columns: 1fr;
    grid-template-rows: 56px 1fr;
    grid-template-areas:
      "topbar"
      "content";
  }
  .layout-notebook__outline,
  .layout-notebook__toc { display: none; }
}""",
        "jsx": """\
export default function NotebookLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="layout-notebook">
      <header className="layout-notebook__topbar">{/* topbar */}</header>
      <nav className="layout-notebook__outline">{/* outline */}</nav>
      <main className="layout-notebook__content">{children}</main>
      <nav className="layout-notebook__toc">{/* table of contents */}</nav>
    </div>
  );
}""",
    },
    {
        "id": "lab",
        "name": "Lab",
        "keywords": ["lab", "experiment", "data", "science", "research", "analysis", "notebook"],
        "css": """\
.layout-lab {
  display: grid;
  grid-template-columns: 220px 1fr;
  grid-template-rows: 48px 1fr 48px;
  grid-template-areas:
    "topbar topbar"
    "sidebar cells"
    "topbar  footer";
  min-height: 100vh;
}

.layout-lab__topbar  { grid-area: topbar; display: flex; align-items: center; gap: 0.5rem; }
.layout-lab__sidebar { grid-area: sidebar; display: flex; flex-direction: column; overflow-y: auto; }
.layout-lab__cells   {
  grid-area: cells;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 1rem;
  overflow-y: auto;
}
.layout-lab__footer  { grid-area: footer; display: flex; align-items: center; }

@media (max-width: 768px) {
  .layout-lab {
    grid-template-columns: 1fr;
    grid-template-rows: 48px 1fr 48px;
    grid-template-areas:
      "topbar"
      "cells"
      "footer";
  }
  .layout-lab__sidebar { display: none; }
}""",
        "jsx": """\
export default function LabLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="layout-lab">
      <header className="layout-lab__topbar">{/* toolbar */}</header>
      <aside className="layout-lab__sidebar">{/* file tree */}</aside>
      <main className="layout-lab__cells">{children}</main>
      <footer className="layout-lab__footer">{/* status */}</footer>
    </div>
  );
}""",
    },
    {
        "id": "creator_shell",
        "name": "Creator Shell",
        "keywords": ["creator", "social", "feed", "post", "profile", "content", "stream"],
        "css": """\
.layout-creator-shell {
  display: grid;
  grid-template-columns: 72px 600px 1fr;
  grid-template-rows: 1fr;
  min-height: 100vh;
}

.layout-creator-shell__nav    { display: flex; flex-direction: column; align-items: center; gap: 1rem; padding: 1rem 0; }
.layout-creator-shell__feed   { display: flex; flex-direction: column; gap: 1.5rem; padding: 1.5rem 0; overflow-y: auto; }
.layout-creator-shell__aside  { display: flex; flex-direction: column; gap: 1rem; padding: 1.5rem; overflow-y: auto; }

@media (max-width: 768px) {
  .layout-creator-shell {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr 56px;
  }
  .layout-creator-shell__nav   { flex-direction: row; justify-content: space-around; padding: 0 1rem; order: 2; }
  .layout-creator-shell__feed  { order: 1; }
  .layout-creator-shell__aside { display: none; }
}""",
        "jsx": """\
export default function CreatorShellLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="layout-creator-shell">
      <nav className="layout-creator-shell__nav">{/* icons */}</nav>
      <main className="layout-creator-shell__feed">{children}</main>
      <aside className="layout-creator-shell__aside">{/* suggestions */}</aside>
    </div>
  );
}""",
    },
    {
        "id": "marketplace",
        "name": "Marketplace",
        "keywords": ["marketplace", "shop", "store", "ecommerce", "product", "catalog", "buy", "sell"],
        "css": """\
.layout-marketplace {
  display: grid;
  grid-template-rows: 64px 1fr auto;
  grid-template-areas:
    "header"
    "body"
    "footer";
  min-height: 100vh;
}

.layout-marketplace__header { grid-area: header; }
.layout-marketplace__body   {
  grid-area: body;
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 0;
}
.layout-marketplace__filters { overflow-y: auto; padding: 1.5rem; }
.layout-marketplace__grid    {
  padding: 1.5rem;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1.5rem;
  align-content: start;
}
.layout-marketplace__footer { grid-area: footer; }

@media (max-width: 768px) {
  .layout-marketplace__body { grid-template-columns: 1fr; }
  .layout-marketplace__filters { display: none; }
  .layout-marketplace__grid { grid-template-columns: repeat(2, 1fr); gap: 1rem; padding: 1rem; }
}""",
        "jsx": """\
export default function MarketplaceLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="layout-marketplace">
      <header className="layout-marketplace__header">{/* header */}</header>
      <div className="layout-marketplace__body">
        <aside className="layout-marketplace__filters">{/* filters */}</aside>
        <main className="layout-marketplace__grid">{children}</main>
      </div>
      <footer className="layout-marketplace__footer">{/* footer */}</footer>
    </div>
  );
}""",
    },
]

_DEFAULT_ARCHETYPE_ID = "operations_console"


def select_archetype(visual_direction: str) -> dict:
    direction_lower = visual_direction.lower()
    for archetype in ARCHETYPES:
        for keyword in archetype["keywords"]:
            if re.search(r"\b" + re.escape(keyword) + r"\b", direction_lower):
                return archetype
    return next(a for a in ARCHETYPES if a["id"] == _DEFAULT_ARCHETYPE_ID)


def generate_layout_css(archetype: dict) -> str:
    css: str = archetype["css"]
    if "@media (max-width: 768px)" not in css:
        archetype_id = archetype["id"].replace("_", "-")
        css = css + f"\n\n@media (max-width: 768px) {{\n  .layout-{archetype_id} {{ grid-template-columns: 1fr; }}\n}}"
    return css


def generate_layout_jsx(archetype: dict) -> str:
    return archetype["jsx"]
