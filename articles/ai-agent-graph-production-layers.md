---
title: "5種類のグラフは1つのDBに入らない。本番のレイヤー設計"
emoji: "🏗"
type: "tech"
topics: ["AI", "ナレッジグラフ", "LangGraph", "Neo4j", "設計"]
published: true
---

:::message
**本シリーズ 第3部**（全3部）: [第1部](https://zenn.dev/knowledge_graph/articles/ai-agent-five-graph-types)で 5 種類の地図、[第2部](https://zenn.dev/knowledge_graph/articles/ai-agent-graph-specialization)で 6 つの特殊化を整理しました。本記事は **どの問いをどの物理層に置くか** と、エージェントへの渡し方を扱います。

**前提**: ナレッジグラフの基礎は「[ナレッジグラフ入門](https://zenn.dev/knowledge_graph/articles/knowledge-graph-intro)」「[RAG を超える知識統合](https://zenn.dev/knowledge_graph/articles/beyond-rag-knowledge-graph)」で扱っています。
:::

第1部・第2部で役割を分けたあと、現場でよく出るのが「全部 Neo4j に入れれば足りるか」です。関係をたどる問いには向きますが、似た障害探しや件数集計は、別のストアの方が向くことが多いです。

本記事では、架空の障害 **INC-001**（製品 Acme Search、顧客 Globex Corp）を題材に、同じデータへ問いを順にぶつけ、Markdown 断片とグラフ（必要なら層分離）で何が返るかを見ます。デモが示すのは、エージェントに **正確な情報をどう渡すか** までです。チケット更新や承認など、世界を変える操作は扱いません。

手元での再現手順は [experiment README](https://github.com/DevRev-JP/tech-blog/tree/main/experiments/ai-agent-graph-production-layers) にあります。本記事では、問いごとの出力と、そこから分かることだけを追います。

---

## データ環境

使うメモ断片は次のとおりです。ソースごとに粒度が違い、関係の型はありません。

```text
[jira]    INC-001: Acme Search の検索レイテンシ悪化。顧客は Globex Corp。
[slack]   globex-support: 検索が遅い。別チケット INC-099 も同じ症状？
[email]   From: ops@globex.example — 障害報告。製品 Acme Search。
[runbook] ログ基盤障害時は先に logging pipeline を復旧してから INC を調査する。
[note]    先週 P0 が 3 件。Acme Search が多い気がする（根拠なし）。
```

同じ世界を、次の層にも載せています。

| 層 | 持つもの |
| --- | --- |
| Neo4j | チケット→製品→顧客、同一性、権限、依存、イベント鎖 |
| Qdrant | 過去障害の埋め込み（類似検索） |
| SQLite | 監査ログ（P0 昇格の件数集計） |
| LangGraph | 実行の現在状態とコンテキストの組み立て |

以降の出力は `./run_demo.sh compare`（AI なし）で得たものです。各問いで「ファイル」は上のメモだけ、「グラフ」は層を分けて取り出した事実です。類似障害と件数集計では、全部を Neo4j から取った場合も並べます。

---

## Q1. このチケットの顧客は？

**問い**: INC-001 の顧客は誰か。

| 渡し方 | 結果 |
| --- | --- |
| ファイル | jira は Globex、slack は顧客名なし、email は製品のみ → 推測 |
| グラフ | INC-001 → Acme Search → Globex Corp → 確定 |

```text
ファイル  ▲ 推測  断片ごとに粒度が違う
          → jira: Globex Corp / slack: 顧客名なし / email: 製品のみ
グラフ    ◎ 確定  Neo4j KG
          → customer: Globex Corp
```

メモだけでは断片ごとに言い方が違います。製品と顧客の関係をたどれると、顧客名を確定できます。

---

## Q2. Slack とメールは同一顧客か？

**問い**: チャネル `globex-support` と `ops@globex.example` は同じ顧客か。

| 渡し方 | 結果 |
| --- | --- |
| ファイル | 文字列が並ぶだけ → 別顧客と誤認しやすい |
| グラフ | どちらも Globex Corp に SAME_AS → 同一と確定 |

```text
ファイル  ▲ 推測  SAME_AS がない
          → slack: globex-support / email: ops@globex.example
グラフ    ◎ 確定  Neo4j SAME_AS
          → same_customer: True, customer: Globex Corp
```

見た目の似た文字列だけでは足りません。同一性の関係があると、根拠つきで答えられます。

---

## Q3. このエージェントは見てよいか？

**問い**: `agent_guest` は INC-001 を閲覧してよいか。

| 渡し方 | 結果 |
| --- | --- |
| ファイル | 「秘匿を答えるな」と書くしかない → 混ざれば漏れる |
| グラフ | CAN_READ が無い → False（本文を渡さない） |

```text
ファイル  ✗ 不可  CAN_READ 型がない
グラフ    ◎ 確定  Neo4j CAN_READ → False
```

権限はプロンプトの注意書きではなく、取得前に評価できる関係として持つと遮断できます。

---

## Q4. ログ基盤の影響範囲は？

**問い**: ログ基盤が落ちたとき、何が止まるか。

| 渡し方 | 結果 |
| --- | --- |
| ファイル | runbook の叙述はあるが、機械は辿れない |
| グラフ | BLOCKS で Search API を返す |

```text
ファイル  △ 一部可  叙述のみ
グラフ    ◎ 確定  Neo4j BLOCKS → ['Search API']
```

手順書の文章より、依存の関係を辿る方が影響範囲を機械的に取れます。

---

## Q5. 類似の過去障害は？

**問い**: いまの障害に意味的に近い過去チケットは何か。

ここから、「全部を関係 DB に入れた場合」も並べます。

| 渡し方 | 結果 |
| --- | --- |
| ファイル | キーワード一致の断片だけ |
| Neo4j 単体 | タイトルに search が付く INC-001 だけ |
| 層分離 | Qdrant で INC-00042, INC-00017 |

```text
ファイル      ▲ 推測  キーワード一致のみ
Neo4j単体     ▲ 推測  ベクトル層なし → ['INC-001']
層分離        ◎ 確定  Qdrant → ['INC-00042', 'INC-00017']
```

関係をたどる Graph DB だけでは、意味的な近さの検索が弱くなります。埋め込みの層が要ります。

---

## Q6. 過去30日の P0 トップ製品は？

**問い**: 過去30日の P0 昇格件数で、製品の順位は何か。

| 渡し方 | 結果 |
| --- | --- |
| ファイル | 「多い気がする」だけ → 集計不可 |
| Neo4j 単体 | Issue.severity 固定値 → Acme Search が 1 件 |
| 層分離 | audit_log 集計 → Acme Search 2、Platform Logging 1 |

```text
ファイル      ✗ 不可  GROUP BY 不可
Neo4j単体     ▲ 推測  Issue.severity だけ → Acme Search: 1
層分離        ◎ 確定  SQLite → Acme Search: 2, Platform Logging: 1
```

件数集計を Cypher に押し込むと、監査ログとずれます。SQL の層が向きます。

---

## Q7. P0 昇格の30分前は？

**問い**: P0 に昇格する30分前に、何が起きていたか。

| 渡し方 | 結果 |
| --- | --- |
| ファイル | 時系列の関係がない → 不可 |
| グラフ | リリース → レイテンシ悪化 → 昇格、と辿れる |

```text
ファイル  ✗ 不可  時系列 Edge なし
グラフ    ◎ 確定  Neo4j Event + BEFORE
          → Release v2.3.1 deployed（14:00）
          → Latency spike detected（14:25）
          → 昇格（14:30）
```

この問いは Neo4j のイベント鎖で足ります。類似や集計のように層を足す必要はありません。分けるべき問いと、分けなくてよい問いがあります。

---

## Q8. エージェントに見せてよいエンティティは？

**問い**: この障害対応で、エージェントに見せてよいエンティティはどれか。

Q1〜Q7 は障害そのものへの問いです。ここだけは、答えを出す前に「どこまで見せるか」を決める問いです。メモ全文を渡すと、毎回どの断片が入るか揺れます。スコープをあらかじめ決めておくと、見せる対象が固定されます。

| 渡し方 | 結果 |
| --- | --- |
| ファイル | jira / slack / email … 断片名が並ぶだけで、範囲がブレやすい |
| グラフ | エンジニア用スコープに INC-001・Acme Search・Globex だけが含まれる |

```text
ファイル  ▲ 推測  断片セットがブレる
グラフ    ◎ 確定  ['INC-001', 'acme-search', 'globex']
```

見せる範囲を固定すると、エージェントに渡す材料が安定します。

---

## まとめ

同じ障害データでも、問いが変わると必要な関係や置き場が変わります。

1. 顧客・同一性・権限・依存は、メモより型付きの関係が要る
2. 類似はベクトル、件数は SQL が向き、全部を Graph DB に押し込むと弱くなる
3. 時間軸のように、Neo4j だけで足りる問いもある
4. 見せるエンティティの範囲を固定すると、エージェントへの材料が安定する

第1部の地図 → 第2部の特殊化 → 本記事の配置、で設計が一連でつながります。手元では `./run_demo.sh setup` のあと `compare`（精度表）と `agent`（同じ問いを LLM に渡す）で再現できます。手順は [experiment README](https://github.com/DevRev-JP/tech-blog/tree/main/experiments/ai-agent-graph-production-layers) を参照してください。

---

## 関連記事

| テーマ | 記事 |
| --- | --- |
| 本シリーズ 第1部 | [ナレッジグラフだけじゃない。AIエージェントが使う5種類のグラフ](https://zenn.dev/knowledge_graph/articles/ai-agent-five-graph-types) |
| 本シリーズ 第2部 | [AIプラットフォームのグラフ特殊化](https://zenn.dev/knowledge_graph/articles/ai-agent-graph-specialization) |
| 形式レイヤ・Workflow Engine | [LLM 依存度を下げる業務 AI アーキテクチャ設計](https://zenn.dev/knowledge_graph/articles/llm-formal-layer-architecture) |
| DevRev KG 実装の深度 | [DevRev ナレッジグラフアーキテクチャ深掘り](https://zenn.dev/knowledge_graph/articles/devrev-kg-architecture-deep-dive) |
| Polyglot Persistence | [Martin Fowler の説明](https://martinfowler.com/bliki/PolyglotPersistence.html) |

---

## 更新履歴

- 2026-07-16: 初版公開

---

## フィードバック受け付け

内容に誤りや追加情報があれば、Zenn のコメントよりお知らせください。
