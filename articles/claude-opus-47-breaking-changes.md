---
title: "Claude Opus 4.7の破壊的変更まとめ（400回避チェックリスト付き）"
emoji: "🧩"
type: "tech" # tech: 技術記事 / idea: アイデア
topics: ["Claude", "生成AI", "Opus", "API", "ナレッジグラフ"]
published: true
---

# Claude Opus 4.7の破壊的変更まとめ（400回避チェックリスト付き）

Claude Opus 4.7（`claude-opus-4-7`）へ更新すると、「今まで動いていたのに急に 400 になる」タイプの変更がいくつかあります。
本記事は、公式の移行ガイドをもとに **400 回避の最短チェックリスト**に落とし込みます。後半で「モデル更新のたびに全面チューニング」にならないための設計（外部レイヤ）も最小限だけ触れます。
本記事は主に **Opus 4.6 → 4.7** の移行を想定しています（3.x など過去世代からの移行チェックは、公式ガイドのチェックリストを参照してください）。

補足しておくと、Anthropic は継続的にモデルを改善し、機能（例：高解像度画像）や安全性（例：サイバーセーフガード）もアップデートしていく企業です。本記事はそれを前提に、変更点を誠実に整理し、実務の移行をスムーズにすることを目的にしています。

---

## この記事の要点

- **破壊的変更（400）**: `thinking.budget_tokens`、サンプリングパラメータ（非デフォルト値）、assistant の `prefill` が代表例です
- **運用上の副作用**: thinking 表示の既定値変更、トークン数の増加（最大 +35%）、画像トークン増（最大 4,784 tokens/枚）を見落としやすいです
- **長期の観点**: モデル更新のたびに再チューニングが膨らまないよう、LLM 呼び出しの境界（アダプタ）と外部レイヤで影響範囲を局所化します

---

## まず自分の該当を判定する（最短）

- **Messages API を直接叩いている**: この記事のチェックリストがそのまま該当します
- **Managed Agents を使っている**: 本記事（Messages API の移行チェック）とは対象が異なり、公式ガイド上は「モデル名の更新以外は不要」です
- **thinking を UI で見せている**: `thinking.display` の既定値が変わるため、表示や体感に影響します
- **画像を投げる**: 画像トークンの再予算が必要です

---

## 破壊的変更（400 エラーになるもの）

一次情報は公式の移行ガイドです（日本語）。

- [Claude 移行ガイド（Opus 4.7 / 4.6）](https://platform.claude.com/docs/ja/about-claude/models/migration-guide)

### 1) Extended thinking の固定予算が廃止（`budget_tokens` は 400）

Opus 4.7 では `thinking: {type: "enabled", budget_tokens: N}` が **400** になります。
代替は adaptive thinking です。

```json
{
  "model": "claude-opus-4-7",
  "max_tokens": 64000,
  "thinking": { "type": "adaptive" },
  "output_config": { "effort": "high" },
  "messages": [{ "role": "user", "content": "..." }]
}
```

- **ポイント**: Opus 4.7 では thinking はデフォルトでオフです。必要なら明示します
- **ポイント**: `effort` は推論の深さとトークン消費のトレードオフです（後述）

関連一次情報:

- [Adaptive thinking](https://platform.claude.com/docs/ja/build-with-claude/adaptive-thinking)
- [effort](https://platform.claude.com/docs/ja/build-with-claude/effort)

### 2) サンプリングパラメータ（非デフォルト値）が 400

Opus 4.7 では `temperature` / `top_p` / `top_k` を **デフォルト以外の値**で送ると **400** になります。
最も安全な移行パスは「payload から完全に省略」です。

やることはこれだけです。

- `temperature` を payload から削除
- `top_p` を payload から削除
- `top_k` を payload から削除

補足:

- `temperature = 0` を使っていた場合も、移行後はそのまま通りません
- そもそも `temperature = 0` は以前から同一出力を保証していなかった、と移行ガイドでも注意されています

「決定論っぽさ」が必要な場合は、サンプリングではなく **構造化出力**と **入力の安定化**に寄せるほうが、長期的に壊れにくいです。

### 3) assistant message の prefill が 400

assistant メッセージを「途中まで入れて続きを生成させる」プリフィルは **400** になります。
代替は以下です。

- 構造化出力
- system prompt で形式制約
- `output_config.format`

最小例（「形を固定する」ことが目的です。中身はユースケースに合わせてください）:

```json
{
  "output_config": {
    "format": {
      "type": "json_schema",
      "schema": {
        "type": "object",
        "properties": {
          "answer": { "type": "string" }
        },
        "required": ["answer"],
        "additionalProperties": false
      }
    }
  }
}
```

---

## 静かな変更（400 にはならないが、移行時に効いてくる）

公式ガイドでも「破壊的変更（400）」とは別に、**デフォルト値や振る舞いが変わる**項目があります。エラーにならないぶん、移行で見落としやすいのでここで分けて整理します。

### thinking 表示の既定値変更（`thinking.display`）

Opus 4.7 では thinking ブロック自体は返るものの、デフォルトでは `thinking` フィールドが空です（400 にはなりません）。
UI で thinking を表示していたり、進捗を見せていたりすると「沈黙が長い」ように見えます。

必要なら以下を明示します。

```json
{
  "thinking": { "type": "adaptive", "display": "summarized" }
}
```

## 破壊ではないが、移行時に効いてくる動作の変更

Opus 4.7 は Opus 4.6 よりも「指示に忠実」で、同時に「出力の癖が変わる」部分があります。ここを十分に確認しないと、移行後にプロンプト調整が増えやすくなります。

- **より文字通りに解釈**: 暗黙の一般化をしない。精度は上がるが明示が要る
- **応答長が可変**: 期待する分量があるならプロンプトで指定する
- **トーンが変わり得る**: スタイルが重要ならスタイルプロンプトを再評価する
- **effort を厳密に尊重**: `low/medium` で複雑タスクを投げると浅くなるリスクがある
- **ツール呼び出しが減り得る**: 必要なら `effort` を上げる、または「いつツールを使うか」を明示する

ここは「最新が出たらチューニングし続ける」になりやすいポイントです。
次の節のように、設計でチューニング対象を減らすのが現実的です。

### effort の選び方（移行時の目安）

公式ガイドでは `xhigh`（超高努力）が Opus 4.7 で追加され、**コーディングとエージェント用途の起点として推奨**されています。

- **まずは `high`**: 多くの intelligence-sensitive なユースケースの下限
- **コーディング/エージェントは `xhigh` 起点**: 品質とトークンのバランスが取りやすい
- **`low/medium`**: レイテンシ最優先の短いタスク向け（複雑タスクでは浅くなるリスクがある）

---

## コスト影響（移行時に見落としやすいところ）

単価が据え置きでも、実運用のコストは変わります。
公式発表でも、Opus 4.6 と同じ単価（入力/出力が $5 / $25 per MTok）で提供される一方、トークン数や effort によって総量が変わり得る点に注意が促されています。

### 1) 新トークナイザーで最大 +35%

同じテキストでも、Opus 4.7 では \(1.0 \sim 1.35\) 倍のトークンになる可能性があります（コンテンツ依存）。
公式ガイドではこの項目も「破壊的変更」として挙げられていますが、実態としては 400 というより **`max_tokens` 設計とコスト見積もり**に影響するタイプの変更です。
そのため、移行時は以下をセットで見直すのが安全です。

- `max_tokens` のヘッドルーム
- トークン見積もり（固定の文字数換算などをしているコードパス）
- 圧縮やコンパクションのトリガー

### 2) 高解像度画像で最大 4,784 tokens/枚

Opus 4.7 は高解像度画像（長辺 2576px）に対応し、フル解像度画像は最大で約 3 倍の画像トークンになります（以前は約 1,600 tokens/枚が上限）。
画像ワークロードがある場合は、移行を機に「必要ならダウンサンプルする」を運用に入れるのが確実です。

---

## 変更に備える設計（再チューニングを最小化する）

ここが本題です。
破壊的変更のたびにプロンプトを全面再チューニングする運用は、長期的にコストが膨らみやすくなります。
モデルは更新され続ける前提で、**影響範囲を局所化する設計**を先に置くほうが、エンジニアとして健全です。

### 1) LLM 呼び出しをアダプタに閉じ込める

`temperature` が消えた、`thinking` が変わった、`prefill` が禁止になった。
この種の変更は「LLM 呼び出しの近く」で起きます。

したがって、アプリのコアから見たときに

- 「LLM に投げる payload を組み立てる層」
- 「出力を受けて正規化する層」

を薄く分離しておくと、破壊的変更が来ても改修範囲が限定されます。

### 2) 外部レイヤ（ナレッジグラフ/Context Graph）で LLM を制御する

モデル更新の影響を増幅させやすいのは、LLM に「長文を丸ごと渡す」前提で、入力の形や根拠の持ち方が曖昧なまま運用する形です。
外部レイヤに **事実・関係・状態・出典**を構造化して保持し、LLM には「いま必要な材料」だけを渡すと、次が効きます。

- **プロンプト再チューニングの対象が減る**（長文の言い回し依存を減らせる）
- **トークン増の影響を受けにくい**（ID、短い抜粋、関係を中心に渡せる）
- **構造化出力と相性が良い**（出力の契約を固定しやすい）

ここではこの種の外部レイヤを「**コンテキスト制御レイヤ**」（LLM の外側で、渡す材料と根拠を制御する層）として扱います。

この「外部レイヤを RAG の外側に置く」整理は、別記事で詳述しています。ここでは重複を避けます。

- [RAGを超える知識統合](https://zenn.dev/knowledge_graph/articles/beyond-rag-knowledge-graph)
- [Claude の外側に Context Graph を](https://zenn.dev/knowledge_graph/articles/context-graph-improves-llm)

### 3) ゴールデンセットを資産化する

モデル更新のたびに「何が悪化したか」を主観で追うと、チューニングが終わりません。
代表ケースだけでよいので、以下を固定して比較できるようにします。

- 入力（問い合わせ）と期待する出力の形
- 根拠（参照 ID、該当箇所）
- コスト（入力/出力トークン、レイテンシ）

外部レイヤがあると、根拠の取り回しがしやすくなります。

---

## 企業向けソリューション例：Shared MemoryでClaudeを安定運用する

ここまでの設計は内製でも可能ですが、企業ユースケースでは「構造化データ（SoR）＋非構造化データ」を両方扱い、かつ権限・監査・運用まで含めて継続的に回す必要があり、実装負荷が跳ね上がりがちです。
その例として、DevRev は Claude に対して Shared Memory（同社の文脈では Context Graph と表現）を提供する形を取ります。

DevRev CTO office の **Jeff Smith** の公開投稿では、「同じ Claude を使っていても、データ取得の仕方（fetch型 vs memory型）で、トークン量や速度、正確性の傾向が変わり得る」という整理がされています（参考文献）。

- fetch型（Skills/MCP 等で都度取得）: セッションごとに schema 探索・関係の再構築が発生し、トークンと時間が増えやすい
- Shared Memory（Context Graph）型: 権威ある関係（typed edge）を “読む” 前提で、join/filter を決定的に処理し、必要な結果セットだけを Claude に渡す

投稿内では、同一ビジネスクエリの反復という前提で、**トークン量を約 95% 減（約 3.2M → 約 157k）**、時間も **約 5.5 倍高速化**といった目安が示されています（環境・データ量・実装に依存するため、自社では実測が前提です）。

中規模以上のユースケースで「構造化＋非構造化」を統合し、LLM の更新（Opus 4.7 のような破壊的変更や挙動変化）の影響を受けすぎない運用を目指す場合、この手の Shared Memory / Context Graph という外部レイヤは、選択肢の一つになります。

---

## 実務チェックリスト（最短で安全に移行する）

- [ ] `temperature` / `top_p` / `top_k`（非デフォルト値）を payload から削除
- [ ] `thinking: {type: "enabled", budget_tokens: N}` を撤去し、`thinking: {type: "adaptive"}` へ
- [ ] `output_config.effort` を決める（まずは `high`、エージェント/コーディングは `xhigh` 起点）
- [ ] assistant の `prefill` を撤去し、構造化出力（`output_config.format`）へ
- [ ] thinking を UI 表示するなら `thinking.display: "summarized"`
- [ ] 新トークナイザー前提で `max_tokens` と見積もりを再確認（固定換算があるなら再テスト）
- [ ] 画像ワークロードがあるならダウンサンプル運用と再予算
- [ ] 代表ケース（ゴールデンセット）で、精度/コスト/レイテンシを再ベースライン

---

## 参考文献

- [移行ガイド（日本語）](https://platform.claude.com/docs/ja/about-claude/models/migration-guide)
- [Adaptive thinking（日本語）](https://platform.claude.com/docs/ja/build-with-claude/adaptive-thinking)
- [effort（日本語）](https://platform.claude.com/docs/ja/build-with-claude/effort)
- [Introducing Claude Opus 4.7（公式発表, 2026-04-16）](https://www.anthropic.com/news/claude-opus-4-7)
- [Right or wrong - flip a coin?（Jeff, LinkedIn）](https://www.linkedin.com/pulse/right-wrong-flip-coin-jeff-smith-0frke/)
- [Your AI starts from zero every morning — the costs compound（Jeff, LinkedIn）](https://www.linkedin.com/pulse/your-ai-starts-from-zero-every-morning-costs-compound-jeff-smith-wnele/)

## 更新履歴

- 2026-04-18: 初版公開

## フィードバック受け付け

内容に誤りや、よりよい実測方法（移行時の比較観点など）があれば、Zenn のコメントで教えてください。
