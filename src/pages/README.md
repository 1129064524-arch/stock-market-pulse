# Page Modules

- `MarketRadar.jsx`: market breadth, mover table, focus stock, and sector linkage.
- `SignalPoolPage.jsx`: explainable rule-signal queue.
- `ResearchWorkspace.jsx`: market-level and single-signal AI research.
- `WatchlistPage.jsx`: locally persisted personal watchlist.
- `AlertsPage.jsx`: rule-event and personal alert history.
- `ReviewPage.jsx`: post-close review workspace.

Each page receives data and actions from `App.jsx`; page files do not fetch or persist data directly.
