# 第3部 構成案

## タイトル候補

| # | タイトル | 狙い |
|---|---------|------|
| 1 | 5種類のグラフは1つのDBに入らない——本番のレイヤー設計 | 「入らない」が直感に引っかかる。技術者が気になる |
| 2 | AIエージェント基盤のレイヤー設計——5種類のグラフをどこに置くか | シリーズ読者に親切。検索にも強い |
| 3 | ファイルからグラフへ、グラフからプラットフォームへ | 成熟段階の話が伝わる。AI-DLC対比が活きる |
| 4 | AIエージェントのグラフを本番で動かす——Polyglot Persistenceという選択 | 技術キーワード直球。アーキテクト層に刺さる |

## Slug候補

- `ai-agent-graph-production-layers`
- `ai-agent-polyglot-persistence`
- `ai-agent-graph-layer-design`
- `ai-agent-graph-platform-architecture`

### 推奨（2026-07-12）

| 項目 | 推奨 | 理由 |
|------|------|------|
| タイトル | **#1** 5種類のグラフは1つのDBに入らない——本番のレイヤー設計 | シリーズ読者の「で、どう置くの？」に直球。第1部タイトルとの対比が効く |
| slug | `ai-agent-graph-production-layers` | 本番配置が主題であることが slug から伝わる |

**命名規則**: experiment ディレクトリは **記事 slug と同じ**（`experiments/ai-agent-graph-production-layers/`）。既存の `kg-no-rag` / `kg-puzzle-agent` / `formal-layer` と同じ慣習。題材の「障害対応」は README・seed データで示す。

---

## 前提

- 第1部: 5種類の分類（地図）
- 第2部: 特殊化カタログ（切り出し基準）
- 第3部: レイヤー配置（どこに置くか、どう組むか）

読者: 第1部・第2部を読んだ技術者。**小規模チーム**（1〜3人で LangGraph / Dify / n8n / Neo4j を触っている層）。
「分類は分かった。で、本番でどう配置するのか」「自分の手元でどこまで再現できるか」に答える記事。

**本記事の主役**: LangGraph・Dify/n8n・Neo4j で**組み合わせ**を組む読者。
**DevRev**: 統合プラットフォームの参考実装（1〜2箇所 + 関連記事リンク）。宣伝ではなく「段階2の完成形の一例」。

---

## 構成

### 1. はじめに：5種類は分かった。で、どこに置くのか

- 第1部で5種類、第2部で6つの特殊化を整理した
- 「全部Neo4jに入れればいい」「LangGraphで全部やる」とはならない理由
- クエリパターンごとに最適な物理層が異なる。ここが本番設計の核心

---

### 2. 成熟段階：ファイル → 単一DB → Polyglot Persistence

3段階の成熟度モデルを提示。AI-DLCを段階0の例として自然に位置づける。

| 段階 | 表現 | 典型例 | 限界が来るとき |
|------|------|--------|--------------|
| 0: ファイルベース | MD + JSON + ディレクトリ構造 | AI-DLC Workflows, CLAUDE.md, LLM Wiki | チーム横断、マルチエージェント、横断クエリ |
| 1: 単一グラフDB | Neo4j / FalkorDB に全部載せる | 多くのGraphRAG実装 | クエリパターンの多様化、レイテンシ要件 |
| 2: Polyglot Persistence | 用途別に物理層を分ける | 本番AIプラットフォーム | ← 本記事のメイントピック |

**小規模チーム向けツール対応**（段階ごとに「何を触ればよいか」）:

| 段階 | 5種類のグラフ | 小規模で触れるツール | 備考 |
|------|-------------|---------------------|------|
| 0 | タスク・手順・ルールの叙述 | SKILL.md, `AGENTS.md`, AI-DLC の workflow MD | 第1部・第2部と一貫。「否定しない」 |
| 0→1 | ナレッジグラフの固定 | Neo4j + Cypher seed | `ai-agent-graph-production-layers` |
| 1 | 実行順序・ステート | **LangGraph**（Python） | ステートグラフ・DAG をコードで表現 |
| 1 | ワークフロー（承認・差し戻し） | **Dify** / **n8n**（GUI） | 循環付き業務フロー。LangGraph と役割分担を図で示す |
| 1→2 | 意味 + 権限 + 監査の分離 | Neo4j + SQLite + LangGraph | `ai-agent-graph-production-layers` 内で完結 |
| 2 | 類似検索 + 関係たどりの併用 | Neo4j + Qdrant | `ai-agent-graph-production-layers` 内で完結 |

ポイント:
- 段階0を否定しない。始めるならファイルで十分
- 段階1で「全部Graph DBに入れて遅い/混乱する」が起きる
- 段階2は「1つの論理グラフを、クエリパターンごとに最適な物理層で引く」設計
- **Dify/n8n は「ワークフローグラフの GUI 実装」、LangGraph は「ステートグラフ + エージェント制御」** と役割を分けて書く（名称争いはしない）

---

## 技術選定：負荷と入れ方の判断

**原則（experiment）**: `ai-agent-graph-production-layers` **だけで完結**する。`kg-puzzle-agent` / `formal-layer` / `kg-no-rag` 等への**実行依存・深掘りリンクは禁止**。記事本文から他 experiment へ誘導してもよいが、**ハンズオンの完了条件は本ディレクトリのみ**。

**原則（記事）**: Graphiti / Zep / Graphify / Dify 等は記事で触れる。experiment には載せない（または最小の宣言的代替で足す）。

### SQLite でいいか？

**結論: はい。ただし役割を「監査・集計・セッション永続」に限定する。**

| 用途 | SQLite で十分か | 理由 |
|------|----------------|------|
| 監査グラフ（誰がいつ何をしたか） | ✅ | SQLite `audit_log` + Neo4j `:AuditAction` + `PERFORMED` Edge（本 experiment 内） |
| 集計（P0件数トップ製品） | ✅ | SQLite GROUP BY |
| LangGraph セッション再開 | ✅（任意） | `SqliteSaver` |
| 時間軸グラフ（いつ・その前に何が） | ✅ | Neo4j `:Event` + `BEFORE` / `CAUSED_BY` / `valid_from`（**宣言的 seed**。Graphiti 不要） |
| 専用 Time Series DB の代替 | ❌ PoC では不要 | 記事で卒業先として1行 |

**PoC の最小物理層（4層）**:

```
Neo4j（宣言的KG + 権限 traversal）
  + Qdrant（類似障害）
  + SQLite（監査・集計）
  + LangGraph in-memory（現在ステート、+ 任意 SqliteSaver）
```

Inverted Index・専用 TS DB は **省略可** と記事に明記。6層モデルは「本番の地図」、4層は「小規模チームの縮小版」。

### 指定ツールの triage（experiment 外＝記事のみ）

| ツール | experiment | 記事 |
|--------|-----------|------|
| **Graphiti / Zep** | 入れない | 本番の時系列KGの例。PoC は Neo4j `:Event` で代替 |
| **Graphify** | 入れない | §4 付録（コードベースKG） |
| **OPA** | 入れない | 権限は Neo4j `CAN_READ` traversal で完結（第2部どおり別 DB 不要） |
| **LightRAG / GraphRAG** | 入れない | §4 推論的の文献リンク |
| **Dify / n8n** | 入れない | Mermaid のみ。ワークフロー実行は LangGraph + Neo4j `WF_TRANSITION` |

### その他の候補（指定外）

| 候補 | 層・役割 | 入れ方 | おすすめ度 | メモ |
|------|---------|--------|-----------|------|
| **LangGraph SqliteSaver** | ステートグラフ永続（セッション跨ぎ） | ai-agent-graph-production-layers に **任意で数行** | ★★★ | 負荷ほぼゼロ。§7 in-memory の「再開」例に使える |
| **Mem0** | ユーザー/session 単位の長期メモリ（ベクトル中心） | 記事で1段落 | ★★☆ | Zep/Graphiti との差は「会話から事実を蒸留」vs「時系列KG」。個人化チャット向き |
| **Cognee** | ドキュメント群 → KG（ECL パイプライン） | 記事で1段落 | ★★☆ | 社内 PDF/Slack を KG 化する **構築フェーズ** の話。運用中の障害エージェントとは段階が違う |
| **MemGPT / Letta** | 仮想コンテキスト（ページング） | 記事で1段落 | ★☆☆ | グラフではない。「メモリ＝グラフだけではない」対比用 |
| **FalkorDB** | Graph DB（Neo4j 代替） | 記事で1行 | ★☆☆ | 本 experiment は Neo4j 前提 |
| **Temporal / Airflow** | 実行順序グラフ（DAG）エンジン | 記事で1行 | ★☆☆ | experiment では LangGraph が DAG |
| **GraphRAG (MS)** | 推論的・コーパス全体グラフ | 記事リンクのみ | ★★★ | experiment では `stage0` 断片が推論的の対照 |
| **Kuzu / DuckDB** | 組み込み Graph / OLAP | 記事で脚注 | ★☆☆ | SQLite と同様「小規模の選択肢」。本編では SQLite に統一して読者の負荷を下げる |

### メモリ系の整理（記事用の1枚図）

```
                    ┌─────────────────────────────────────┐
                    │  エージェントが参照する「記憶」        │
                    └─────────────────────────────────────┘
         ┌──────────────┬──────────────┬──────────────────┐
         │ ターン内      │ セッション跨ぎ  │ 組織・業務の事実    │
         ├──────────────┼──────────────┼──────────────────┤
         │ LangGraph    │ SqliteSaver  │ Neo4j (宣言的KG)  │
         │ state        │ / checkpoint │ Cypher seed       │
         ├──────────────┼──────────────┼──────────────────┤
         │ コンテキスト  │ SqliteSaver  │ Neo4j Event 鎖   │
         │ グラフ(部分)  │ (再開)       │ (宣言的時間軸)    │
         ├──────────────┼──────────────┼──────────────────┤
         │ 類似検索      │ —            │ Qdrant / 埋め込み  │
         └──────────────┴──────────────┴──────────────────┘
```

（experiment 内で完結する記憶の割り当て。Zep/Mem0 は記事の本番例のみ。）

**記事での書き分け**:
- **ナレッジグラフ**（第1部）≠ **エージェントメモリ**（本節）≠ **GraphRAG**（検索補強）— 3つを混ぜない
- Graphiti/Zep は「メモリ」のうち **時間軸・エピソード** に強い
- Mem0 は「メモリ」のうち **ユーザー個人化** に強い
- Graphify は「メモリ」ではなく **リポジトリの事前インデックス**（段階0→1 のショートカット）

### 更新後の ai-agent-graph-production-layers 構成（要約）

詳細は下記「ハンズオン設計」のディレクトリツリーを正とする。ここでは物理層だけ要約。

```
Neo4j [1][2][4] + LangGraph [3][5] + Qdrant + SQLite（集計のみ・グラフではない）
段階0のみ fragments.json（対照）
```

**Q5〜Q7 の割り当て**（第2部6特殊化を本 experiment だけでカバー）:

| ID | 質問 | 第2部特殊化 | 実装 |
|----|------|------------|------|
| Q5 | 過去30日の P0 件数トップ製品は？ | 監査（集計） | SQLite |
| Q6 | Slack とメールは同一顧客か？ | **同一性** | Neo4j `SAME_AS` |
| Q7 | P0 昇格の30分前に何があったか？ | **時間軸** | Neo4j `:Event` + `BEFORE` |
| Q8 | このターンで LLM に渡したノードは？ | **コンテキスト** | `layers/context_graph.py`（近傍サブグラフ） |
| （Q1〜Q8） | 下表参照 | 第1部KG + 6特殊化 | `stage2` |

---

### 記事本文向け：「この機能にはこのOSS」対応表

記事§3または§7に載せる読者向けの表。2段階（PoC推奨 / 本番で必要になるもの）で整理。

#### PoC（段階1〜2の縮小版）で推奨

| やりたいこと | 推奨OSS | 一言理由 |
|------------|---------|---------|
| 関係のtraversal（KG・権限・依存） | **Neo4j** (Community) | エコシステム最大。Cypher の可読性が高い。コンテナ1つ |
| 意味的類似検索（類似障害・コンテキスト） | **Qdrant** | セルフホスト可、軽量、REST API がシンプル |
| 集計・監査ログ | **SQLite** | ファイル1個。追加コンテナ不要。GROUP BY / JOIN の問いに |
| エージェントの状態遷移制御 | **LangGraph** | State Graph のコード表現。Python で完結 |
| 権限ポリシーの宣言的管理 | **Neo4j** `CAN_READ` traversal | 第2部どおり権限グラフを KG 上の Edge で表現。OPA は記事で言及のみ |
| ワークフロー（承認・差し戻し）の可視化 | **Dify** / **n8n** | GUI で循環付きフローを設計。LangGraph と役割を分ける |

#### 本番（段階2フル）で必要になるが、PoCには重いもの

| やりたいこと | 本番向きOSS | なぜPoCに入れないか | いつ必要になるか |
|------------|------------|-------------------|----------------|
| 時系列（イベント鎖） | **Neo4j** `:Event` + `BEFORE` | experiment 内で宣言的 seed。ingest 不要 |
| エピソードからの動的抽出 | **Graphiti** (OSS) | **experiment 外**。記事の本番例 |
| Graphitiのマネージド運用 | **Zep** | **experiment 外**。記事の本番例 |
| ドキュメント群からKGを自動構築 | **Cognee** | ECLパイプラインの構築フェーズはPoC題材（障害対応）と別 | 社内PDF・Slack・Confluenceを一括でKG化する初期セットアップ時 |
| コーパス全体のコミュニティ要約＋検索 | **GraphRAG** (Microsoft) | インデックス構築のトークンコストが大きい | 「全社ドキュメントから未知の関連を発見したい」推論的検索が主目的のとき |
| コードベースのKG化 | **Graphify** | 障害対応題材とドメインがずれる。環境差が大きい | 「自社リポジトリをエージェントの地図にしたい」開発者向けのナレッジ構築時 |
| 実行順序のdurable execution | **Temporal** | コンテナ＋設定＋学習コストが高い | 数日〜数週間かかるワークフローを、途中で死んでも再開保証したいとき |
| 専用Time Series DB | **TimescaleDB** / InfluxDB | PoC規模ではSQLiteの `escalated_at` で十分 | イベント量が万単位/日を超え、時間範囲クエリのレイテンシが問題になったとき |
| CDCでKGリアルタイム更新 | **Debezium** → Neo4j | パイプライン設計が重い | 外部システム（CRM、チケット管理等）の変更を即座にKGに反映したいとき |
| 全文検索 (Inverted Index) | **Elasticsearch** / Meilisearch | PoC規模ではNeo4j full-text indexで代替可 | テキスト量が大きくなり、Graph DBのfull-text検索では遅いとき |

**記事での書き方**:
- PoC表は「これだけで段階2の縮小版が動く」と断言
- 本番表は「PoCの先で、この問いが出たらこのOSSを検討する」というロードマップ
- 「本番で必要」は「今すぐ入れろ」ではなく「いつ必要になるかの判断基準」を示す

---

### 3. Polyglot Persistence：1つの論理グラフを複数の物理層で持つ

DevRevの6層Polyglot Persistenceをモデルにした一般論として書く。

| 物理層 | 担うクエリパターン | 5種類+特殊化との対応 |
|--------|-------------------|---------------------|
| Graph DB | 関係のtraversal（多ホップ推論） | ナレッジグラフ、依存関係、権限、同一性 |
| Inverted Index | キーワード検索・フィルタ | ナレッジグラフ（テキスト属性） |
| Embeddings DB | 意味的類似検索 | コンテキストグラフ（類似検索・近傍探索） |
| Analytical Store (SQL) | 集計・フィルタ・JOIN・ダッシュボード | ワークフロー実行ログ、監査グラフ |
| Time Series DB | 時間範囲クエリ・変化追跡 | 時間軸グラフ、ステートグラフ遷移履歴 |
| In-memory Store | リアルタイム状態参照（ミリ秒） | ステートグラフ（現在の状態）、ダッシュボード |

核心メッセージ:
- 「KGだからGraph DB」は短絡的
- 同じKGのNodeでも、テキスト検索はInverted Index、類似検索はEmbeddings、関係たどりはGraph DBで引く
- 1つの論理エンティティが複数の物理層に存在する。同期はwrite-time enrichmentで担保

---

### 4. 宣言的Graph vs 推論的Graph

第2部で伏線を張らなかった分、ここで回収する。

| | 宣言的（Ontology-first） | 推論的（Inferred） |
|---|---|---|
| 構築 | スキーマ（オントロジー）を先に定義。データを流し込む | ドキュメントの共起・行動パターンから動的に構築 |
| 代表例 | DevRev KG, Palantir Foundry, 社内マスタDB | Glean, Google Enterprise KG, GraphRAG |
| 劣化パターン | オントロジーが現実と乖離したときだけ劣化 | データパターンが変わると静かに劣化（人の異動、命名規則変更等） |
| 立ち上げ速度 | スキーマ設計が必要（2-4週間） | データを入れればすぐ動く |
| アクション安全性 | 高い（根拠が明示的に辿れる） | 低い（推論に基づくアクションは事故リスク） |
| 向いている場面 | エージェントがアクションを取る（チケット作成、ステータス変更） | ドキュメント検索、レコメンデーション |
| 小規模での例 | Cypher seed、Neo4j 権限 traversal | `stage0` 断片（推論的の対照） |
| 開発者向けの別ルート | **Graphify**（tree-sitter で `EXTRACTED` 関係をローカル生成） | Graphiti ingest（エピソードから LLM 抽出） |

**付録（experiment 外・1段落）**: 障害対応以外に「自社コードをエージェント地図にしたい」読者向けに Graphify を触れる。関係に `EXTRACTED` / `INFERRED` / `AMBIGUOUS` タグが付く点は、アクション前に人が確認すべき境界の説明に使える。

核心メッセージ:
- 「検索」だけなら推論的でも許容できる
- 「アクション」を取らせるなら宣言的Graphの方が安全
- エージェントが「たぶん関係がある」レベルの推論でアクションを取ると事故になる

---

### 5. トークンコストと応答速度：事前計算の効果

定量データを入れて説得力を持たせる。

| 方式 | トークン消費 | レイテンシ | 特徴 |
|------|------------|-----------|------|
| Schema exploration（毎回APIで関係を発見） | ~3Mトークン | ~9分 | クエリのたびにフルスキャン |
| KG traversal（事前に関係を保持） | ~150Kトークン | ~1.5分 | traversalコストのみ |
| 差分 | **95%削減** | **5.5x高速** | |

なぜこうなるか:
- schema explorationは「テーブル一覧を取得→カラムを読む→JOINキーを推測→クエリを組む→実行→結果を読む」を毎回やる
- KG traversalは「このNodeの隣接Edgeを辿る」だけ。関係は事前にwrite-timeで計算済み

「GraphRAGで精度が上がる」だけでなく「コストが桁違いに下がる」が本番での決定打。

出典: DevRev Agent Studio enablement資料（公開資料として引用可能か要確認）

---

### 6. 「組み合わせ」vs「統合プラットフォーム」

| | 組み合わせ | 統合 |
|---|---|---|
| 構成例 | Neo4j + LangGraph + Airflow + OPA + TimescaleDB | DevRev, Palantir等 |
| 立ち上げ | 各ツールに習熟が必要 | 1つ覚えれば動く |
| 柔軟性 | 各層をベストオブブリードで選べる | プラットフォームの制約を受ける |
| 整合性 | レイヤー間の同期を自分で保証（ここが最も辛い） | 内部で保証される |
| 運用負荷 | コンポーネント数 × 運用チーム | 1つの運用で済む |
| 向いている組織 | 技術力が高く、自社でインフラを持ちたいチーム | プラットフォームに集中し、差別化は上のレイヤーでやりたい組織 |

核心メッセージ:
- どちらが正しいという話ではない
- 組み合わせの最大の辛さは「レイヤー間の整合性を自分で保証すること」
- 統合プラットフォームの最大の辛さは「プラットフォームの制約に乗ること」

---

### 7. 障害対応エージェントの本番構成（通し題材の着地）

第1部・第2部で使ってきた障害対応エージェントを、段階2（Polyglot Persistence）でどう配置するかの全体図。

```
┌─────────────────────────────────────────────────────────────┐
│  クエリ層（エージェントが叩く）                                   │
│  ・自然言語 → SQL / Graph traversal / Vector search          │
│  ・実装例: LangGraph ノードがルーター + Ollama（ホスト）          │
└──────────────┬──────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────┐
│  ルーティング層（クエリパターンで物理層を選択）                     │
│  ・実装例: 問いの型で分岐（経路 / 類似 / 集計 / 権限）            │
└──────────────┬──────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────┐
│  物理層                                                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐       │
│  │Graph DB  │ │Inverted  │ │Embeddings│ │SQL Store │       │
│  │(権限,依存)│ │Index     │ │DB        │ │(監査,集計)│       │
│  │ Neo4j    │ │(省略可)  │ │ Qdrant   │ │ SQLite   │       │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘       │
│  ┌──────────┐ ┌──────────┐                                 │
│  │Time Series│ │In-memory │                                 │
│  │(時間軸)   │ │(現在状態) │                                 │
│  │ Neo4j*   │ │LangGraph │                                 │
│  └──────────┘ └──────────┘                                 │
│  * 簡易: escalated_at プロパティ。深掘り: Graphiti（記事の本番例・experiment 外）│
└─────────────────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────────────────┐
│  書き込み層（write-time enrichment）                            │
│  ・チケット作成 → Graph + Index + Embeddings + Time Series    │
│    に同時書き込み                                              │
│  ・Dify/n8n はここを Webhook で受け、人の承認後に enrich       │
└─────────────────────────────────────────────────────────────┘
```

障害対応の各場面がどの物理層を叩くかのマッピング:
- 「このチケットに関連する顧客は？」→ Graph DB (ナレッジグラフ traversal)
- 「類似の過去障害は？」→ Embeddings DB (意味的類似検索)
- 「P0に昇格した時刻は？」→ Neo4j `escalated_at` / `:Event`（PoC 完結）。Graphiti は記事の本番例のみ
- 「このエージェントがこのチケットを見てよいか？」→ Graph DB (権限グラフ traversal)
- 「今エージェントはどの状態？」→ In-memory Store (ステートグラフ)
- 「過去30日で障害が多い製品トップ5は？」→ SQL Store (集計)

**小規模チームの現実的な割り当て**（段階2の縮小版）:

| 問い | 最小構成 | 触るコマンド |
|------|---------|-------------|
| 関係たどり（KG） | Neo4j | `stage2` Q1 |
| 類似障害 | Qdrant | `stage2` Q2 |
| 依存関係 | Neo4j `BLOCKS` | `stage2` Q3 |
| 権限 | Neo4j `CAN_READ` | `stage2` Q4 |
| 監査（集計・実行記録） | SQLite + Neo4j `PERFORMED` | `stage2` Q5 + `graphs` |
| 同一性 | Neo4j `SAME_AS` | `stage2` Q6 |
| 時間軸 | Neo4j `:Event` | `stage2` Q7 |
| コンテキスト | 近傍サブグラフ切り出し | `stage2` Q8 |
| エージェント制御 | LangGraph + Ollama | `stage2` / `full` |
| 人の承認・差し戻し | Neo4j `WF_TRANSITION` + LangGraph | `graphs` / `full` |

---

### 8. 手を動かす：段階0→2を CLI で辿る

**新規セクション**（本記事の差別化ポイント）。理論のあとに「自分の Mac で 30 分」パスを置く。

記事内の流れ:
1. 障害対応の **Q1〜Q8** を段階0→1→2で実行
2. 各段階で「何が足りなくなったか」を `=== 確認 ===` ブロックで示す
3. Dify/n8n は **同等のワークフロー図** を記事に載せ、CLI 実験の「人の承認」ステップの代替説明とする

**読者の前提環境**（執筆・検証時）:
- Podman（または Docker）— Neo4j / Qdrant のみコンテナ。SQLite はホスト上の `audit.db`（追加コンテナ不要）
- ホスト Ollama CLI — LLM はコンテナ内に入れない
- Python 3.11+

---

### 9. まとめ

- 5種類のグラフは1つのDBに入らない。クエリパターンで物理層を分ける
- 成熟度は ファイル → 単一DB → Polyglot Persistence の3段階
- 宣言的Graphはアクションの安全性を、推論的Graphは立ち上げ速度を提供する
- 事前計算（write-time enrichment）がトークンコスト95%削減の鍵
- 第1部の地図 → 第2部のカタログ → 第3部の配置図、で設計が完結する
- **第1部の5種類は experiment で全部動く**（`./run_demo.sh graphs` で自己確認）
- **小規模チームでも** `ai-agent-graph-production-layers` 単体で第1部5種・第2部6特殊・段階2縮小版が完走する

---

## ハンズオン設計（experiments）

**単体完結の原則**: 第3部のハンズオンは `experiments/ai-agent-graph-production-layers/` **のみ**。第1部5種類・第2部6特殊化・段階0→2の物理層分離を、**この README のコマンドだけで**完走できること。他 experiment への「続きはこちら」は **README に書かない**（記事の関連記事リンクは可）。

### 方針

| 原則 | 内容 |
|------|------|
| 完結性 | `./run_demo.sh full` で第1部5種 + 第2部6特殊 + 段階0/1/2 を一通り確認 |
| 題材 | 障害対応（INC-001、Acme Search、顧客 Globex） |
| LLM | ホスト Ollama（コンテナ内 Ollama は使わない） |
| コンテナ | Neo4j + Qdrant のみ。SQLite はホスト上 `audit.db` |
| グラフ | タスク・WF・KG・権限・依存・同一性・時間軸は **Neo4j 型付き Edge**。DAG・ステート・WF実行は **LangGraph** |
| ファイル | `fragments.json` は **段階0の対照のみ** |

### 必須：第1部の5種類を OSS で実装する

**シリーズの約束**: 第1部は「ファイル（MD・JSON・チェックリスト）では **Edge の型** が持てないからグラフに進む」と言っている。第3部の experiment もそれを体現する。**グラフの定義と実行はファイル読み込みにしない**（段階0の対照実験を除く）。

| 段階 | 表現 | experiment での役割 |
|------|------|-------------------|
| 0 | ファイル（断片・叙述） | `fragments.json` — **わざと**第1部が批判する形 |
| 1+ | グラフ（Node / Edge に型） | Neo4j（意味・タスク・ワークフロー定義）+ LangGraph（DAG・実行・状態） |

**「グラフを使っている」の判定基準**（実装レビュー用）:
- ✅ Neo4j 上の **ラベル付き Node** と **型付き Relationship** を Cypher で辿れる
- ✅ LangGraph の **StateGraph**（ノード＋有向エッジ。循環含む）としてコンパイルされ、実行される
- ❌ YAML/JSON/Markdown をプロンプトに貼って「手順」と呼ぶ（＝段階0と同型）
- ❌ Python の if/else だけでワークフローを表現（Edge の型が見えない）

| 第1部の5種類 | 問い | グラフとしての実装 | 保存・実行 |
|-------------|------|-------------------|-----------|
| **1. ナレッジグラフ** | 何を知っているか | Neo4j: `Issue`,`Product`,`Customer` + `AFFECTS`,`OWNED_BY`,`BLOCKS` | `data/incident.cypher` → Cypher traversal |
| **2. タスクグラフ** | 何をやるか | Neo4j: `:IncidentTask` + **`:TASK_PREREQUISITE`**（計画前提。実行順序ではない） | `layers/task_graph.py` が Cypher で辿る |
| **3. 実行順序（DAG）** | 処理をどの順で | **LangGraph** 固定有向エッジ: `fetch_context→route_layer→generate`（非巡回） | `graphs/dag_graph.py` + `agent_langgraph.py` |
| **4. ワークフロー** | 業務をどう進めるか | Neo4j: `:WfStep` + **`:WF_TRANSITION {action}`**（`approve`/`reject`）で循環定義。LangGraph が解釈して実行 | `layers/workflow_graph.py` + LangGraph サブグラフ |
| **5. ステートグラフ** | 今どんな状態か | **LangGraph** `AgentState` + 状態遷移エッジ（`investigating→waiting_approval→done`） | `agent_langgraph.py`, 任意 `SqliteSaver` |

**第1部との対応**（同じ Neo4j DB に載せても **ラベルと Edge 型で論理分離**）:

```cypher
// [1部] ナレッジ
(Issue)-[:AFFECTS]->(Product)-[:OWNED_BY]->(Customer)
// [1部] タスク（計画前提）
(:IncidentTask)-[:TASK_PREREQUISITE]->(:IncidentTask)
// [1部] ワークフロー（循環あり）
(:WfStep)-[:WF_TRANSITION {action:'reject'}]->(:WfStep)
// [2部] 同一性
(:ChannelAccount)-[:SAME_AS]->(:Customer)
// [2部] 依存
(:Service)-[:BLOCKS]->(:Service)
// [2部] 権限
(:Agent)-[:CAN_READ]->(:Issue)
// [2部] 時間軸
(:Event)-[:BEFORE]->(:Event)
(:Issue)-[:ESCALATED_AT]->(:Event)
// [2部] 監査
(:Actor)-[:PERFORMED]->(:AuditAction)
```

**Dify/n8n**: GUI で同じワークフローを書く例（記事 Mermaid のみ）。**実行の正本は Neo4j 定義 + LangGraph**。

**`./run_demo.sh graphs`**: Neo4j + LangGraph の **実グラフ**を表示（LLM 不要可）。

```
=== 確認 — 第1部 5種類 ===
[1] KG       : AFFECTS / OWNED_BY
[2] タスク   : TASK_PREREQUISITE
[3] DAG      : LangGraph 固定エッジ（非巡回）
[4] WF       : WF_TRANSITION (approve/reject)
[5] ステート : state.phase

=== 確認 — 第2部 6特殊化（stage2） ===
[権限]     Q4  CAN_READ
[同一性]   Q6  SAME_AS
[依存]     Q3  BLOCKS
[時間軸]   Q7  Event BEFORE
[監査]     Q5  audit_log + PERFORMED
[コンテキスト] Q8 部分グラフ node_ids
```

**`quick` の対照**: `stage0`（JSON断片）vs `graphs`（型付きグラフ）で第1部の主張を再現。

**stage2 との関係**: `graphs`＝第1部5種。`stage2`＝第2部6特殊の **Q1〜Q8**。`full`＝推奨通し。

### 必須：第2部の6特殊化を本 experiment だけでカバー

| 特殊化 | 問い（stage2） | Neo4j / その他の Edge・実装 |
|--------|---------------|---------------------------|
| 権限グラフ | Q4 このエージェントは見てよいか | `CAN_READ` パストラバーサル |
| 同一性グラフ | Q6 Slack とメールは同一顧客か | `SAME_AS`, `ChannelAccount` |
| 依存関係グラフ | Q3 ログ基盤の影響範囲 | `BLOCKS`, `DEPENDS_ON` |
| 時間軸グラフ | Q7 昇格30分前に何が | `:Event`, `BEFORE`, `CAUSED_BY` |
| 監査グラフ | Q5 集計 + graphs で実行記録 | SQLite + `PERFORMED` / `APPROVED` |
| コンテキストグラフ | Q8 このターンで渡した部分グラフ | `SCOPE_INCLUDES` または hop 制限 traversal |

---

**目的**: 同じ5問を段階0→1→2で実行し、「1つのDBに入れない」理由を体感させる。**あわせて第1部5種類をすべて OSS で動かす。**

```
ai-agent-graph-production-layers/
├── README.md                 # 単体完結手順（他 experiment 不要と明記）
├── compose.yaml              # neo4j + qdrant（SQLite は audit.db としてホスト）
├── env.sample
├── requirements.txt
├── run_demo.sh               # setup | graphs | stage0 | stage1 | stage2 | quick | full | guide
├── data/
│   ├── fragments.json        # 段階0のみ
│   ├── incident.cypher       # KG+Task+Wf+権限+依存+同一性+Event+AuditAction（Edge型で分離）
│   ├── incident_docs.jsonl   # Qdrant
│   └── audit_seed.sql        # SQLite audit_log
└── app/
    ├── graphs/
    │   └── dag_graph.py      # [3] LangGraph DAG
    ├── layers/
    │   ├── graph.py          # [1] KG + Q3 依存 + Q4 権限
    │   ├── identity_graph.py # [2部] Q6 SAME_AS
    │   ├── temporal_graph.py # [2部] Q7 Event 鎖
    │   ├── context_graph.py  # [2部] Q8 部分グラフ
    │   ├── audit_graph.py    # [2部] PERFORMED / Q5 集計
    │   ├── task_graph.py     # [1部] TASK_PREREQUISITE
    │   ├── workflow_graph.py # [1部] WF_TRANSITION
    │   └── vector.py         # Q2 Qdrant
    ├── demo_graphs.py        # graphs コマンド: Neo4j + LangGraph の Edge 型を表示
    ├── stage0_fragments.py   # 段階0: 断片直渡し（ファイルの限界）
    ├── stage1_neo4j_only.py  # 段階1: 全部 Neo4j に押し込むつらさ
    ├── stage2_router.py      # 段階2: 5問ルーティング
    └── agent_langgraph.py    # [3][4][5] LangGraph 本体（DAG + workflow 実行 + state）
```

**8問（第1部KG + 第2部6特殊化）**:

| ID | 質問 | 段階0の限界 | 段階2が叩く層 / 特殊化 |
|----|------|------------|----------------------|
| Q1 | このチケットの顧客は？ | 断片のどれを信じるか曖昧 | Neo4j KG |
| Q2 | 類似の過去障害は？ | キーワードのみ | Qdrant（コンテキスト類似） |
| Q3 | ログ基盤障害の影響範囲は？ | 依存が埋もれる | Neo4j **依存** |
| Q4 | このエージェントは見てよいか？ | プロンプト禁止では漏れる | Neo4j **権限** |
| Q5 | 過去30日 P0 トップ製品は？ | 集計不可 | SQLite **監査** |
| Q6 | Slack とメールは同一顧客か？ | 別チケット扱い | Neo4j **同一性** |
| Q7 | P0 昇格の30分前に何が？ | 時系列不可 | Neo4j **時間軸** |
| Q8 | このターンで渡したノードは？ | 毎回違う断片 | **コンテキスト** 部分グラフ |

**run_demo.sh の体験フロー**:

```bash
ollama serve   # 別ターミナル
ollama pull gemma2:2b

cd experiments/ai-agent-graph-production-layers
cp env.sample .env && pip install -r requirements.txt
./run_demo.sh setup
./run_demo.sh graphs     # 第1部5種類の表示確認（数十秒・LLM不要でも可）
./run_demo.sh quick      # stage0 vs stage1
./run_demo.sh stage2     # Q1〜Q8 + ルーティング
./run_demo.sh full       # graphs + stage0 + stage2（推奨通し）
```

**完了条件（すべて本ディレクトリ内）**:

```
[ ] ./run_demo.sh graphs   → 第1部5種の Edge 型が表示される
[ ] ./run_demo.sh stage0   → ファイル断片の限界が出る
[ ] ./run_demo.sh stage2   → 第2部6特殊化が Q1〜Q8 で答えられる
[ ] ./run_demo.sh full     → 上記が連続で通る
[ ] README に他 experiment への実行依存がない
```

**MVP（Must have）**:
- [ ] 第1部5種：Neo4j 型付き Edge + LangGraph StateGraph
- [ ] 第2部6特殊：Q1〜Q8 と `incident.cypher` の seed（`SAME_AS`,`BLOCKS`,`CAN_READ`,`:Event`,`PERFORMED` 等）
- [ ] `layers/{identity,temporal,context,audit}_graph.py`
- [ ] 段階0 / stage1 / stage2 / graphs / quick / full
- [ ] 各 script 末尾 `=== 確認 ===`
- [ ] README 単体完結（他 experiment 不要と明記）

**Better to have**:
- [ ] write-time enrichment のデモ（チケット作成 → Neo4j + Qdrant + SQLite 同時書き込み）
- [ ] `stage1` で「集計を Cypher に押し込むと遅い/読めない」ログ出力
- [ ] LangGraph `SqliteSaver` でセッション再開デモ

**Nice to have**:
- [ ] Dify ワークフロー JSON のサンプル（import 用、実行不要）
- [ ] n8n 相当の Mermaid を README に併記
- [ ] 記事 §4 付録: Graphify の1段落（experiment 化はしない）

### 記事 ↔ experiment 対応表（執筆用）

**ハンズオン節は `ai-agent-graph-production-layers` の README のみ参照**。他 experiment のコマンドは載せない。

| 記事 § | 本文で見せるもの | 読者が叩くコマンド |
|--------|----------------|-------------------|
| §2 | 成熟度3段階 + stage0 対照 | `./run_demo.sh quick` |
| §3 | 6層→4層縮小 | `./run_demo.sh stage2`（ルーティングログ） |
| §4 | 宣言的 vs 推論的 | `./run_demo.sh stage0` vs `graphs` |
| §7 | 障害対応配置図 | `./run_demo.sh full` |
| §8 | クイックスタート | `graphs` → `full` |
| 第2部6特殊 | カタログの着地 | `./run_demo.sh stage2`（Q1〜Q8） |

---

## DevRevの出し方

- 「統合プラットフォーム」の実例としてDevRevを1-2箇所だけ言及
- 既に第2部の関連記事にDevRev KGアーキテクチャ解剖記事がリンクされているので、そこへの接続
- トークンコスト実測値の出典としても使える
- AI-DLCを「段階0」、Neo4j単体を「段階1」、DevRev的な構成を「段階2」

---

## 想定文字数

- 9000-12000文字（第1部・第2部よりやや長め。図と表が多いので読みやすさは維持）
- §8 ハンズオンは 1500〜2000 文字（コマンドブロック + 確認チェックリスト）

## フロントマター案

```yaml
title: "5種類のグラフは1つのDBに入らない——本番のレイヤー設計"
emoji: "🏗"
type: "tech"
topics: ["AI", "ナレッジグラフ", "LangGraph", "Neo4j", "設計"]
published: false
```

---

## 関連記事リンク（挿入予定）

記事本文の背景説明用。**ハンズオンの実行手順には使わない。**

| テーマ | 記事 |
|--------|------|
| 本シリーズ 第1部 | ai-agent-five-graph-types |
| 本シリーズ 第2部 | ai-agent-graph-specialization |
| 形式レイヤ（概念） | llm-formal-layer-architecture |
| DevRev KG 実装 | devrev-kg-architecture-deep-dive |
| Polyglot Persistence（一般論） | https://martinfowler.com/bliki/PolyglotPersistence.html |

## 実装タスク（執筆前）

| 順序 | タスク | 状態 |
|------|--------|------|
| 1 | `ai-agent-graph-production-layers/` 単体完結実装（第1部5種+第2部6特殊+Q1〜Q8） | 未着手 |
| 2 | `./run_demo.sh full` が他 experiment なしで通ることを確認 | 未着手 |
| 3 | 記事ドラフト（`published: false`） | 未着手 |
| 4 | 第1部・第2部の「第3部（執筆予定）」リンクを slug に更新 | 未着手 |
| 5 | 批判的レビュー + URL 検証 | 未着手 |
| 6 | Git Flow（develop → feature → PR → main） | 未着手 |

---

## 執筆時の注意

- 第1部・第2部と同じトーン（断言調、実務向け、冗長な前置きなし）
- 通し題材（障害対応エージェント）を第3部でも使い、着地させる
- DevRevの宣伝にならないよう、一般論として書く。具体名は「ある統合プラットフォームでは」程度
- AWS AI-DLCへの敬意を保つ（「始めるならファイルで十分」の立場は第2部と一貫）
- Polyglot Persistenceは概念として一般的（Martin Fowlerの記事等）なので、DevRev固有の話にしない
- **小規模チーム向け**: PoC は **4層**（Neo4j + Qdrant + SQLite + LangGraph）。6層は本番の地図
- **experiment 単体完結**: README・記事ハンズオンは `ai-agent-graph-production-layers` のコマンドのみ。他 experiment と混ぜない
- **第1部5種**: Neo4j 型付き Edge + LangGraph StateGraph。YAML/MD を正本にしない
- **第2部6特殊**: Q1〜Q8 で本 experiment 内完結（`SAME_AS`, `PERFORMED`, `:Event`, コンテキスト切り出し）
- **Graphiti / Zep**: 記事の本番例のみ。時間軸は Neo4j `:Event` で experiment 内完結
- **SQLite**: 監査集計 + 任意 checkpointer
- トークン95%削減の出典は公開可否を確認してから記載（未確認なら「社内ベンチマークの一例」に留める）
