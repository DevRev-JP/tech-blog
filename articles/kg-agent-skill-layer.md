---
title: "ツールを100個並べてもAIエージェントは賢くならない"
emoji: "🏗️"
type: "tech"
topics: ["AIエージェント", "ナレッジグラフ", "生成AI", "LLM", "アーキテクチャ"]
published: true
---

# ツールを100個並べてもAIエージェントは賢くならない

> この記事は独立して読めます（約8分）

この記事はナレッジグラフを知らなくても読めます。KGが初めての方は「[AIエージェントが毎回データを取りに行く設計の限界](https://zenn.dev/knowledge_graph/articles/kg-agent-memory-first-design)」を先に読んでもよいですが、この記事単独でも理解できます。

---

## 問題：Skillを増やしても精度が安定しない

「Difyでワークフローを30個作った。LangChainでエージェントを20個作った。Claude CodeにSkillを50個入れた。合計すれば100を超えた。どれも動くが全体として管理できない。新しいToolを追加するたびに、既存のエージェントの挙動が変わる」

日本のエンジニアと話すと、この話が頻繁に出てきます。個々のエージェントやワークフローは機能する。しかしスケールしない。チームで管理できない。精度が安定しない。

多くのチームがこの問題を「Skillの定義方法」で解決しようとします。プロンプトを改善する。ツールの説明を詳しく書く。エージェントを分割する。しかし改善しても精度は安定しない。

**原因はSkillの書き方ではありません。Skillが問い合わせている「先」にあります。**

---

## ToolとSkillは各フレームワークで定義が違うが、共通する構造がある

「Skill」「Workflow」「Tool」という言葉はClaude Code、Cursor、Dify、LangChain、CrewAI、Amazon Bedrock Agents全てで使われています。定義は各々異なりますが、どれにも共通する構造があります。

**どのフレームワークでも、SkillやToolは最終的に「どこかのデータソースに問い合わせる」か「どこかに副作用を起こす」のどちらかを行います。**

```mermaid
graph LR
    subgraph "あなたのエージェント"
        A[LLM] --> S[Skill / Tool / Workflow]
    end
    S --> API1[SaaS A の API]
    S --> API2[SaaS B の API]
    S --> API3[SaaS C の API]
    S --> API4[社内DB]
```

この「Skillの先にあるもの」がバラバラの外部APIである限り、以下の問題は**Skillの書き方をいくら改善しても解決しません**。

- LLMは各APIの戻り値を「その場でつなぎ合わせる」しかない
- 同じ顧客が各システムで別名称で存在していても、LLMが「おそらく同じだろう」と推測する
- APIの応答速度がバラバラなのでレイテンシが安定しない
- Tool数が増えるほどスキーマがコンテキストを圧迫し、LLMの選択精度が下がる

---

## 精度を決めるのはSkillの書き方ではなく、その先のデータ基盤

ここで根本的な問いが生まれます。

> **重要なのはどのモデルを使うかではなく、モデルが何の上で推論するか。**

Skillの先にあるデータ基盤が異なると、同じSkill定義でも結果が全く違います。

以下の2つの図は、**全く同じSkill（「顧客Aの直近チケットと担当者を調べる」）**を実行したときの違いです。Skillの定義は同じ。変わるのは先にあるデータ基盤だけです。

### 同じSkillで、先がバラバラのAPIの場合

```mermaid
sequenceDiagram
    participant LLM
    participant Skill as Skill: 顧客調査
    participant CRM as Salesforce
    participant Support as Zendesk
    participant HR as SmartHR

    Note over Skill: 同じSkill定義
    LLM->>Skill: 顧客Aの担当者とチケットを調べて
    Skill->>CRM: 顧客A検索
    CRM-->>Skill: "Acme Corp" / ACC-10045
    Skill->>Support: Acme Corpのチケット検索
    Support-->>Skill: org_887 "Acme" のチケット3件
    Skill->>HR: 担当者検索
    HR-->>Skill: 田中（営業部）
    Skill-->>LLM: 3つの断片を渡す
    Note over LLM: "Acme Corp"と"Acme"は同じ？<br/>田中はどの案件の担当？<br/>→ 推測が必要
    LLM-->>LLM: 回答（推測に依存。実行ごとに揺れる）
```

### 同じSkillで、先が統合されたKGの場合

```mermaid
sequenceDiagram
    participant LLM
    participant Skill as Skill: 顧客調査
    participant KG as ナレッジグラフ（Memory）

    Note over Skill: 同じSkill定義
    LLM->>Skill: 顧客Aの担当者とチケットを調べて
    Skill->>KG: 顧客A → チケット → 担当者（グラフ走査）
    Note over KG: Acme Corp = Acme = 同一ノード（名寄せ済み）<br/>チケット→担当者のエッジが存在
    KG-->>Skill: 顧客Acme / チケット3件 / 担当:田中 / 関係性付き
    Skill-->>LLM: 構造化された事実（推測不要）
    LLM-->>LLM: 回答（事実を解釈するだけ。安定）
```

違いは明確です。**Skillの定義は1文字も変えていません。** 変わったのは問い合わせ先だけです。

バラバラのAPIの場合、LLMは「Acme CorpとAcmeは同じ会社か？」「田中はどのチケットの担当か？」を推測しなければなりません。統合されたKGの場合、それらは既にデータとして解決済みであり、LLMの推測は不要です。

**設計上の帰結**: 同じSkill定義でも、先にある基盤が統合されていれば精度が安定します。LLMの推測領域が最小化されるからです。

---

## なぜナレッジグラフが「統合された先」として機能するか

KGが単なるデータベースと違って「Skillの先」として優れている理由は4つあります。

1. **関係性がエッジとして永続化されている**: 「この顧客は先週も同じ問題を報告している」という関係が、LLMの推測ではなくデータとして存在する
2. **Entity Resolutionが済んでいる**: 「SalesforceのAcme Corp」と「ZendeskのAcme」が同一ノードとして解決済み。LLMが名寄せを推測しない
3. **権限がクエリ層で制御される**: 見てはいけないデータがクエリ結果に混入しない。不正確な情報源が推論に入らない
4. **クエリが決定論的**: Text2SQLやセマンティック検索はLLMの気分で結果が変わらない。推論ではなくデータとして事実が返る

これら4つが合わさると、LLMの「推測」が必要な領域が劇的に狭くなります。推測が減れば、ハルシネーションが減り、精度が安定します。

---

## ナレッジグラフだけでは不十分な領域

KGがあれば全て解決するわけではありません。正直に補足します。

- **KGにデータを入れるコスト**: 50システムのデータをKGに統合するにはリアルタイム同期インフラが別途必要（[AIエージェントが毎回データを取りに行く設計の限界](https://zenn.dev/knowledge_graph/articles/kg-agent-memory-first-design)で詳述）
- **Skillの定義・検証・バージョン管理**: KGがあっても「いつ何をどう問い合わせるか」の定義と検証は別の問題
- **想定外の質問への対応**: 検証済みのパターンにないアドホックな質問には、LLMの即興推論のほうが柔軟な場面もある
- **全てをKG経由にすべきではない**: 外部APIへの書き込み（Slack通知、メール送信等）はKGの外側の操作として残る

重要なのは「KGですべて解決する」ことではなく、**LLMの推測を必要最小限に絞る設計をすること**。KGはその設計を実現する最も効果的な基盤の一つです。

---

## 参照実装：DevRev Computer の設計

DevRev Computerの差別化は、Skillの「定義方法」ではなく、**Skillの先にある基盤（Memory）**にあります。

**Memory = 統合済み・名寄せ済み・権限制御済みのKG**

DevRevでは全てのビジネスデータ（顧客、チケット、Issue、Feature、Developer等）がMemoryという単一のKGに統合されています。SkillはこのMemoryに対してクエリを投げます。バラバラのSaaS APIを叩くのではありません。

**Foundational Services = Memoryへのアクセス手段**

Memoryから事実を取り出す方法として、Text2SQL（構造化データへの問い合わせ）、セマンティック検索（非構造化データの検索）、オブジェクト参照（特定エンティティとその関係の取得）などが用意されています。これらは決定論的な処理であり、LLMの推測ではなく事実を返します。

**Skillの検証基盤**

KGだけでは解決できない「Skillの検証・バージョン管理」を補完するのが、Agent Studioのbuild-test-observe-improveサイクルです。数百件のリアルなクエリでSkillを事前評価し、問題があればロールバックできます。「動いてから評価する」ではなく「評価済みのものだけ本番に出す」設計です。

---

## 今日から始める1ステップ

KGがなくても、今日から始められる最初の一手があります。

**次にやるべき1ステップ：自分のエージェントが呼んでいるToolの「先」を棚卸しする。**

各Toolが何にアクセスしているかを表にしてください。5分で終わります。

| Tool名 | アクセス先 | 統合されているか |
|---|---|---|
| 顧客検索 | Salesforce API | ❌ 個別API |
| チケット検索 | Zendesk API | ❌ 個別API |
| 案件確認 | 社内DB | ❌ 個別API |
| ナレッジ検索 | Confluence API | ❌ 個別API |

この表を書いて、「❌ 個別API」が並んでいるなら、Skillの書き方をどれだけ改善しても精度は安定しません。問題はSkillの先にあります。

エージェントの自律性のレベル分類に興味がある方はこちらも参考になります。  
[AI解像度の高いエンジニア向けのAIエージェント分類](https://zenn.dev/knowledge_graph/articles/ai-agent-classification-for-engineers-2026)

---

**技術リーダーの方へ**: 自社のエージェントのToolが何にアクセスしているかを確認してください。10個のToolが10個の別々のAPIを叩いているなら、それはSkillの書き方ではなくデータ基盤の問題です。

---

AIエージェントを本番に出せない本当の理由（権限管理・監査・ロールバックの設計）はこちらの記事で扱っています。  
[AIエージェントを本番に出せない本当の理由](https://zenn.dev/knowledge_graph/articles/kg-agent-production-safety)

---

## このシリーズの記事

| 記事 | テーマ |
|---|---|
| [AIエージェントが毎回データを取りに行く設計の限界](https://zenn.dev/knowledge_graph/articles/kg-agent-memory-first-design) | scatter-gather問題の設計回答 |
| [ナレッジグラフをエージェントの「記憶」にする設計](https://zenn.dev/knowledge_graph/articles/kg-agent-ontology-design) | スキーマ設計と名寄せ |
| **[ツールを100個並べてもAIエージェントは賢くならない](https://zenn.dev/knowledge_graph/articles/kg-agent-skill-layer)** | **Skillの先にあるデータ基盤の問題（本記事）** |
| [AIエージェントを本番に出せない本当の理由](https://zenn.dev/knowledge_graph/articles/kg-agent-production-safety) | 権限・監査・ロールバック |

---

## 更新履歴

- 2026-05-24: 初版公開

## フィードバック受け付け

本記事は AI を活用して執筆しています。内容に誤りや追加情報があれば、Zenn のコメントよりお知らせください。
