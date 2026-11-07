# A — Current architecture

Status: IN_PROGRESS / NO-GO. This source audit is not an installable release baseline.

| Repository | Audit HEAD | Draft PR |
|---|---|---|
| unified-system | `eb0c6486524c7d7f4d3dc390abebc0107db2c858` | 26 |
| bybit-cluster-grid | `7a19ab40c30efef431bb16f0ddc91960608bf597` | 265 |
| strattester | `a56c24a0f25a0c5ea9222fcd953a49536c91dfc9` | 73 |
| math | `917d99672e37db59835a8ab23b03c99826b12d78` | 112 |
| meta_analyse | `f3c01a23fa5baaeeeb28eb8e9397e72b5ef4d5a1` | 78 |
| Terminan | `10e07ef108d155b9ca2278eec6a8361cb92fa488` | 69 |

LS5 central control; intended coordinators LS5/PC4/PC3, workers PC2/PC1/LS7. PC1 and LS7 require separate Home qualification. ADMINIT excluded from compute inventory and not contacted. Office Consul remains its observed 2/3 state; loopback tests do not change it.

Existing path: Bybit → Grid → Storage → Strattester/Math/MetaAnalyse → existing PaperLedger → Terminan. This is an architectural dependency graph, not evidence that all runtime edges are admitted. Control GET and storage filesystem have isolated implementation evidence; native identity, authoritative publication, scheduler adapters and scientific domain mappings remain blockers. Canonical release/integration-manifest.json remains provisional and not installable.
