---
title: "2026年に注目すべきAIスタートアップ10社（CRN）"
emoji: "🎯"
type: "tech" # tech: 技術記事 / idea: アイデア
topics:
  ["AIスタートアップ", "エンタープライズAI", "AIエージェント", "AIセキュリティ"]
published: true
---

## はじめに

米 IT 系メディア CRN が公開した「The 10 AI Startup Companies to Watch in 2026」では、  
2026 年に向けて存在感を高める AI スタートアップ 10 社が紹介されています。

本記事では、原文の内容をベースに **日本語で要点を整理** しつつ、  
日本のエンジニア視点で「この会社は何をやっていて、どこが本質か」を補足します。

なお掲載順は **CRN の記事順を維持し、DevRev のみ最後** に配置しています。

---

## 1. Anthropic

**※2025年にも選出されており、2年連続で選ばれています。**

Claude シリーズで知られる LLM ベンダー。  
OpenAI とは異なり、当初から「安全性」「エンタープライズ利用」を強く意識した設計思想を持っています。

CRN では、急速な資金調達と大手企業での採用拡大が取り上げられており、2026 年に向けて **高性能かつ統制可能な LLM** という立ち位置を確立しつつある点が評価されています。

LLM を業務に本格投入したい企業にとって、「性能」よりも「事故を起こさない」ことが重要になるフェーズで、存在感を高めつつあるプレイヤーです。

**注目のポイント**

#### 1. 日本市場への本格進出

2025 年 10 月、Anthropic はアジア太平洋地域で初となる**東京オフィス**を開設しました。これに伴い、CEO のダリオ・アモデイ氏が高市早苗総理大臣と会談し、AI 評価手法に関する協力のため、AI セーフティ・インスティテュート（AISI）との覚書に署名しています。また、広島 AI プロセスのフレンズグループへの参加や、森美術館とのパートナーシップ拡大など、単なる営業拠点ではなく、**日本市場への深いコミットメント**を示しています。

#### 2. LLM が従来苦手とされていた分野への進出

Anthropic は、LLM が従来苦手とされていた**金融、政府機関、医療**といった分野に積極的に進出しています。

- **Claude for Financial Services**（2025 年 7 月）: 金融機関向けに特化した AI ソリューション。Anthropic の最新モデルを搭載し、複数の外部データソースと連携することで、金融業界の専門家向けに最適化されています。

- **Claude Gov**（2025 年 6 月）: 米国の国家安全保障機関専用に開発された AI モデル群。政府機関からのフィードバックを基に開発され、実際の運用ニーズや国家安全保障上の要件に対応しています。

- **医療データ連携**（2025 年 7 月）: 米国政府の公的医療保険を管轄する CMS（メディケア・メディケイド・サービスセンター）と連携し、医療情報の相互運用性を高める誓約に署名。病院や診療所ごとに分断された医療データを AI 技術で統合し、患者が自身の健康情報を包括的に把握できるようにすることを目指しています。

これらの動きは、単なる「高性能 LLM」ではなく、**業界固有の要件や規制に対応したソリューション提供**という方向性を示しています。

#### 3. モデル福祉（Model Welfare）研究プログラム

2025 年 4 月、Anthropic は AI が将来的に意識や感情を持つ可能性を検討するため、「モデル福祉（Model Welfare）」と呼ばれる新たな研究プログラムを立ち上げました。このプログラムでは、AI モデルの福祉が道徳的配慮を受けるべきか、その判断方法、AI モデルが示す「苦痛のサイン」の可能性、および簡単に実施できる介入策などを調査しています。これは、**AI の安全性を超えた、より深い倫理的考察**を示す取り組みであり、長期的な視点での AI 開発に対する責任感を示しています。

#### 4. AI 信頼性向上への取り組み強化

2025 年 12 月、Anthropic は AI の安全性と信頼性を高めるための取り組みを強化しました。AI システムが予測可能で意図した通りに動作することを保証するため、AI の動作を人間が理解しやすくする技術開発に注力しています。また、2024 年 8 月には OpenAI とともに、米国商務省標準技術局（NIST）の AI 安全研究所と、AI の安全性に関する研究、試験、評価に関して協力する契約を締結しています。**業界全体の安全性向上への貢献**という姿勢が明確です。

**参考文献**

1. **東京オフィス開設と日本市場への進出**
   - [Anthropic、アジア太平洋地域初の東京オフィスを開設 - マイナビニュース](https://news.mynavi.jp/techplus/article/20251030-3603597/)
   - [Anthropic、東京オフィス開設を発表 - PR TIMES](https://prtimes.jp/main/html/rd/p/000000001.000171496.html)

2. **LLM が従来苦手とされていた分野への進出**
   - [Anthropic、金融機関向け生成 AI ソリューション「Claude for Financial Services」を発表 - AT Partners](https://www.atpartners.co.jp/ja/news/2025-07-16-anthropic-a-large-scale-language-modeler-announces-claude-for-financial-services-a-generative-ai-solution-for-financial-institutions)
   - [Anthropic、米国国家安全保障機関専用の AI モデルを発表 - AT Partners](https://www.atpartners.co.jp/ja/news/2025-06-06-anthropic-a-large-scale-language-modeler-launches-ai-model-dedicated-to-u-s-national-security-agencies)
   - [How Anthropic and CMS Break Data Silos - JobiRun](https://jobirun.com/how-anthropic-and-cms-break-data-silos/)

3. **モデル福祉（Model Welfare）研究プログラム**
   - [Anthropic、AI モデル福祉の研究プログラムを新設 - AT Partners](https://www.atpartners.co.jp/ja/news/2025-04-25-anthropic-a-large-scale-language-modeler-establishes-a-new-research-program-on-ai-model-welfare)

4. **AI 信頼性向上への取り組み**
   - [Anthropic、AI システムの信頼性向上への取り組みを強化 - Miralab](https://miralab.co.jp/media/anthropic-ai-reliability/)
   - [Anthropic と OpenAI、NIST の AI 安全研究所と協力契約を締結 - 窓の杜](https://www.watch.impress.co.jp/docs/news/1619983.html)

---

## 2. Airia

Airia は、AI エージェントを企業環境で安全に動かすための**制御・オーケストレーション基盤**を提供しています。

CRN では「PoC は成功するが、本番運用で止まる企業が多い」という現実に対し、Airia がそのギャップを埋める存在として紹介されています。

LLM やエージェント自体ではなく、

- どこまで AI に権限を与えるか
- 何を実行させてよいか
- どう監視するか

といった **運用レイヤ**にフォーカスしている点が特徴です。

**注目のポイント**

#### 1. PoC から本番運用へのギャップを埋める具体的な機能

2025 年 12 月、Airia は **AI Security** と **Agent Orchestration** という 2 つの主要機能を発表しました。これらは、まさに CRN が指摘する「PoC は成功するが、本番運用で止まる」という課題に対する具体的な回答となっています。

**AI Security** では、AI エージェントのセキュリティ体制管理、既知の攻撃パターンや脆弱性に対するテスト、エージェントのアクセス制御、データのマスキングや暗号化などを通じて、AI エージェントの安全な運用を支援します。

**Agent Orchestration** では、AI エージェントのロジックやデータフローの定義、プロンプトや LLM のテスト、エンタープライズデータへの安全な接続、モデルのパフォーマンス比較やコスト管理など、エージェントの効率的な運用をサポートします。

これらの機能は、単なる「エージェント開発ツール」ではなく、**本番環境で AI エージェントを安全に運用するための包括的なプラットフォーム**として設計されています。

#### 2. セキュリティとオーケストレーションの統合アプローチ

Airia の特徴は、セキュリティとオーケストレーションを**統合的に提供**している点です。多くの企業では、セキュリティと運用管理が別々のツールやプロセスで管理されており、その結果として「セキュリティを確保すると運用が複雑になる」「運用を簡素化するとセキュリティが甘くなる」というジレンマが生じています。

Airia は、この 2 つを最初から統合して設計することで、**セキュリティを確保しながらも運用を効率化**することを可能にしています。これは、エンタープライズ環境で AI エージェントを本格導入する際の大きな障壁を解消するアプローチです。

#### 3. 業界特化型ソリューションの展開

Airia は、小売業界向けの AI エージェント活用事例やソリューションを提供しています。これは、汎用的なプラットフォームだけでなく、**業界固有の要件に対応したソリューション**を展開していることを示しています。

PoC から本番運用への移行においては、業界ごとの規制や要件が大きな障壁となります。Airia が業界特化型ソリューションを提供することで、**より具体的な導入支援**が可能になると考えられます。

**参考文献**

1. **AI Security 機能**
   - [Airia AI Security - Airia.com](https://airia.com/wp-content/uploads/sites/7/2025/12/Airia_Security__A4-December_2025.pdf)

2. **Agent Orchestration 機能**
   - [Airia Agent Orchestration - Airia.com](https://airia.com/wp-content/uploads/sites/7/2025/12/Airia_Orchestration_A4-December_2025.pdf)

3. **小売業界向けソリューション**
   - [Airia Blog - Airia.com](https://airia.com/blog/)

---

## 3. Aurascape

Aurascape は AI ネイティブなセキュリティ企業です。  
人間が操作する前提ではなく、**AI が生成・操作するデータ**を守ることを主眼にしています。

CRN では、AI 活用が進むほど攻撃対象も変化している点が強調されており、Aurascape はその変化に正面から向き合う存在として取り上げられています。

「AI を入れた結果、セキュリティリスクが増える」という状況に対する新しい回答の一つと言えます。

**注目のポイント**

#### 1. AI ネイティブエンジンによる動的な制御

Aurascape のプラットフォームは、**AI ネイティブエンジン**を搭載しており、従来のセキュリティソリューションでは難しかった AI とのインタラクションの可視化と制御を実現しています。従来のセキュリティツールは、人間が操作する前提で設計されているため、AI が生成・操作するデータの動的な特性に対応することが困難でした。

Aurascape は、AI の動的な性質を前提に設計されたセキュリティプラットフォームとして、**リアルタイムでの可視化と制御**を提供しています。これにより、企業は AI アプリケーションの使用状況を包括的に把握し、迅速なセキュリティ対策を可能にしています。

#### 2. 迅速なコネクタ開発による対応力

Aurascape は、**48 時間以内に本番環境向けのコネクタを開発・展開するサービスレベル契約（SLA）**を導入し、2,200 以上の AI アプリケーションに対応しています。これは、AI アプリケーションの急速な普及に伴うセキュリティリスクに迅速に対応するための重要な手段です。

企業が新たな AI ツールを導入する際、セキュリティ対応が遅れることで導入が停滞するケースが多く見られます。Aurascape の迅速なコネクタ開発により、**新たな AI ツールの導入時にもセキュリティを確保**しやすくなり、企業の AI 活用を加速させることができます。

#### 3. 包括的な AI アプリケーションの可視化

2,200 以上の AI アプリケーションを網羅するデータベースは、企業が自社の AI 利用状況を正確に把握し、適切な管理を行う上で有益です。これにより、**シャドー IT のリスクを低減**し、コンプライアンスの強化が期待できます。

AI アプリケーションの利用が広がるにつれて、IT 部門が把握していない AI ツールの利用（シャドー AI）が増加しています。Aurascape の包括的な可視化機能により、企業は自社の AI 利用状況を正確に把握し、適切なガバナンスを実現できます。

**参考文献**

1. **AI アプリケーション発見機能**
   - [Aurascape AI Application Discovery - Aurascape.ai](https://aurascape.ai/aurascape-ai-application-discovery/)

2. **AI アクティビティ制御セキュリティプラットフォーム**
   - [Aurascape、AI アクティビティ制御セキュリティプラットフォームを発表 - GenerativeD](https://www.generatived.com/news/aurascape-unveils-ai-activity-control-security-platform)

3. **RSA Conference 2025 での発表**
   - [RSA Conference 2025 現地レポート - GF Design](https://gf-design.jp/2025/05/19/rsa2025/)

---

## 4. Imbue

Imbue は AI コーディングの文脈で語られることが多い企業ですが、CRN では **推論能力を持つエージェント型 AI** の研究開発企業として紹介されています。

単なるコード補完ではなく、

- タスクを分解する
- 状態を保持する
- 次の行動を判断する

といった「考えながら作業する AI」を目指している点が特徴です。

LLM を「便利なツール」ではなく**実行主体として扱う方向性**を最も強く打ち出しているプレイヤーの一社です。

**注目のポイント**

#### 1. 推論能力の強化に特化した基盤モデル開発

Imbue は、AI エージェントが複雑なタスクを自律的に遂行できるよう、**推論能力の強化に特化した基盤モデル**の開発を進めています。これは、単なるコード補完やタスク実行を超えた、**「考えながら作業する AI」**を実現するための取り組みです。

従来の LLM は、プロンプトに対して応答を生成する「反応型」の動作が中心でしたが、Imbue が目指すのは、タスクを分解し、状態を保持し、次の行動を判断する**「能動型」の AI エージェント**です。これにより、エンジニアのコーディング支援や政策提案の分析など、多様な分野での応用が期待されます。

#### 2. 大規模な計算資源への投資

Imbue は、Dell Technologies と 1 億 5,000 万ドルの契約を締結し、約 10,000 台の NVIDIA H100 Tensor Core GPU を備えた高性能コンピューティングクラスターを構築しています。この大規模な投資は、同社の AI モデル開発に対する強いコミットメントを示しています。

推論能力の強化には、従来の LLM トレーニングよりもはるかに大規模な計算資源が必要となります。Imbue がこの規模の投資を行うことは、**推論能力の強化が単なる研究目標ではなく、実用的な AI エージェントを実現するための必須要件**であることを示しています。

#### 3. 安全性と信頼性を重視した開発アプローチ

Imbue は、AI エージェントの安全性と信頼性を確保するため、**研究主導の安全対策と整合性メカニズム**を導入しています。これにより、ユーザーがタスクを委任し、結果を検証し、プロジェクト目標を反復的に達成することが可能となります。

AI エージェントが自律的に動作する際、安全性と信頼性は最も重要な課題です。Imbue が独立系 AI 研究企業として、特定の企業や業界の影響を受けにくい環境で研究開発を進めている点は、**純粋な研究開発に集中できる**という利点があります。

**参考文献**

1. **Dell Technologies との契約と高性能コンピューティングクラスター**
   - [Imbue to Develop Next-Generation AI Models with $150 Million Dell High Performance Computing System - PR Newswire](https://www.prnewswire.com/news-releases/imbue-to-develop-next-generation-ai-models-with-150-million-dell-high-performance-computing-system-301998808.html)

2. **Imbue の AI エージェントに関する情報**
   - [Imbue Ai for Reasoning Agents & Intelligent Automation - AI Bucket](https://www.aibucket.io/tools/imbue)

---

## 5. Mistral AI

Mistral AI はオープンウェイト LLM を中心に展開するフランス発の AI 企業です。

CRN では、クローズドモデル一強になりがちな市場に対して、「自社運用・自社管理できる LLM」という現実的な選択肢を提供している点が評価されています。

クラウド依存を避けたい企業や、自社要件に合わせてモデルを制御したいケースでは、2026 年に向けてさらに存在感が高まると見られています。

**注目のポイント**

#### 1. オープンウェイトモデルによる市場の多様化

Mistral AI は、オープンウェイトの LLM を提供することで、**クローズドモデル一強の市場に多様性をもたらす**存在として注目されています。2025 年 9 月には評価額が 140 億ドルに達したと報じられており、設立から短期間で急成長を遂げています。

オープンウェイトモデルは、企業が自社環境でモデルを運用・管理できるため、**データ主権やコンプライアンス要件を満たしやすい**という利点があります。特に、クラウド依存を避けたい企業や、自社要件に合わせてモデルを制御したいケースでは、Mistral AI のモデルは現実的な選択肢となっています。

#### 2. 多様な用途に対応するモデル展開

Mistral AI は、Mistral Large 3、Ministral 3、コーディング用の Codestral など、**多様な用途やデバイスに対応したモデル**をリリースしています。これにより、幅広いニーズに対応する戦略が伺えます。

特に、Ministral 3 はモバイルデバイス向けに最適化されており、2025 年 2 月には AI アシスタント「Le Chat」を iOS および Android 向けにリリースし、一般消費者市場への進出を強化しています。**エンタープライズからコンシューマーまで、幅広い市場をカバー**する戦略が明確です。

**参考文献**

1. **Mistral AI の企業概要と最新動向**
   - [Mistral AI - Wikipedia](https://en.wikipedia.org/wiki/Mistral_AI)

2. **新 AI モデル「les Ministraux」リリース**
   - [Mistral AI、スマホでも使える新 AI モデル「les Ministraux」リリース - ITmedia](https://www.itmedia.co.jp/news/articles/2410/17/news128.html)

3. **コーディング用生成 AI モデル「Codestral」リリース**
   - [Mistral AI、コーディング用生成 AI モデル「Codestral」リリース - ITmedia](https://www.itmedia.co.jp/news/articles/2405/30/news139.html)

---

## 6. Perplexity

**※2025年にも選出されており、2年連続で選ばれています。**

Perplexity は検索と生成 AI を組み合わせたプロダクトで知られています。

CRN では、単なるチャットボットではなく**最新情報を前提にした回答体験**を提供している点が注目されています。

RAG（Retrieval-Augmented Generation）の実用形がそのままプロダクトになった例とも言え、情報探索のインターフェースを変えつつある存在です。

**注目のポイント**

#### 1. RAG の実用化と情報探索の変革

Perplexity は、RAG（Retrieval-Augmented Generation）の実用形をそのままプロダクト化した存在として注目されています。リアルタイムのウェブ検索機能を組み合わせ、最新のインターネットコンテンツに基づいて回答を生成し、**使用した情報源を明示的に引用する**特徴があります。

これは、従来の検索エンジンと LLM の単純な組み合わせではなく、**情報探索のインターフェースそのものを変革する**取り組みです。ユーザーは、検索結果のリストから情報を探すのではなく、AI が統合した回答を直接受け取ることができます。

#### 2. AI ブラウザ「Comet」による統合体験

2025 年 7 月、Perplexity は AI 駆動のウェブブラウザ「Comet」をリリースしました。このブラウザは、Perplexity の検索エンジンと統合されており、記事の要約や画像の説明、トピックの調査、メールの作成など、多様なタスクを実行できます。

これは、検索エンジンからブラウザへと**プラットフォームを拡張**する戦略であり、ユーザーの情報探索体験をより包括的にサポートすることを目指しています。検索だけでなく、**情報の消費と活用までを統合**した体験を提供する方向性が明確です。

#### 3. 急速な成長と市場での評価

Perplexity AI は、設立からわずか数年で急速に成長し、2025 年 9 月時点で**200 億ドルの評価額**に達したと報じられています。この急成長は、AI 駆動の検索エンジンに対する市場の強い需要と、同社の革新的な技術力を示しています。

従来の検索エンジン市場は Google が圧倒的なシェアを持っていましたが、Perplexity は**AI 時代の新しい検索体験**を提供することで、市場に新たな選択肢をもたらしています。2026 年に向けて、情報探索の方法がさらに多様化していく可能性があります。

**参考文献**

1. **Perplexity AI の企業情報と製品概要**
   - [Perplexity AI - Wikipedia](https://en.wikipedia.org/wiki/Perplexity_AI)

2. **AI ブラウザ「Comet」の詳細**
   - [Comet (browser) - Wikipedia](https://en.wikipedia.org/wiki/Comet_%28browser%29)

---

## 7. Project Prometheus

Project Prometheus は Jeff Bezos 主導の大型 AI プロジェクトです。

CRN では、短期的なプロダクトよりも**製造・航空宇宙などの産業基盤レベル**で AI を適用する長期視点の取り組みとして紹介されています。

ROI がすぐに見えない領域に大規模投資を行う点が特徴で、2026 年以降に成果が表に出てくるタイプのプロジェクトです。

**注目のポイント**

#### 1. 物理世界への AI 応用を目指す長期戦略

Project Prometheus は、2025 年 11 月に Jeff Bezos が設立した AI 新興企業で、コンピュータ、航空宇宙、電気自動車などの分野で、エンジニアリングや製造業務を支援する AI 技術の開発に注力しています。これは、AI の適用範囲を**デジタル領域から物理的な領域へと拡大**する重要な試みです。

従来の AI は主にソフトウェアやデータ処理の領域で活用されてきましたが、Project Prometheus は**製造・航空宇宙などの産業基盤レベル**で AI を適用することを目指しています。これは、ROI がすぐに見えない領域への大規模投資であり、2026 年以降に成果が表に出てくる長期視点の取り組みです。

#### 2. 異例の規模の資金調達と人材確保

Project Prometheus は、設立初期段階で**62 億ドル（約 6,800 億円）**という異例の規模の資金を調達しています。また、OpenAI、Google DeepMind、Meta などのトップ AI 企業から約 100 名の研究者を採用しており、**豊富な資金力と優秀な人材**を確保しています。

この規模の投資と人材確保は、Jeff Bezos の AI 分野への強いコミットメントを示しています。また、彼が共同 CEO として直接経営に関与することは、単なる投資家ではなく、**経営者として AI 分野に本格参入**する意図が明確です。

#### 3. Blue Origin とのシナジー可能性

Jeff Bezos は宇宙開発企業 Blue Origin の創業者でもあり、Project Prometheus と Blue Origin の間には**シナジーの可能性**があります。航空宇宙分野での AI 活用は、Blue Origin の事業と直接関連しており、AI 技術の物理世界への応用を加速させる戦略的な意図が伺えます。

このように、Project Prometheus は単なる AI スタートアップではなく、**Jeff Bezos の既存事業との統合を視野に入れた戦略的プロジェクト**として位置づけられています。2026 年以降、物理世界への AI 応用がどのように進展するか、注目されている存在です。

**参考文献**

1. **Project Prometheus の企業概要**
   - [Project Prometheus (company) - Wikipedia](https://en.wikipedia.org/wiki/Project_Prometheus_%28company%29)

2. **資金調達と事業領域**
   - [ベゾスの神秘的な AI 企業「Project Prometheus」が 62 億ドルのシードラウンドを調達 - AIbase](https://www.aibase.com/ja/news/22885)

---

## 8. WitnessAI

WitnessAI は、AI モデルやエージェントの**ガバナンス・可視化・管理**を目的とした企業です。

CRN では、

- 誰がどの AI を使っているのか
- 何を実行させているのか

を把握できないまま AI が導入されている企業が多い現状が指摘されています。

WitnessAI は、その「見えなさ」を解消するレイヤとして位置づけられています。

**注目のポイント**

#### 1. シャドー AI の可視化と制御

WitnessAI は、2024 年 10 月に「Secure AI Enablement Platform」の商用提供を開始しました。このプラットフォームは、従業員が ChatGPT などのサードパーティ AI アプリケーションを使用する際の**可視性と制御**を提供し、データ漏洩を防止します。

また、2024 年 9 月には Microsoft 365 Copilot および GitHub Copilot との統合を発表し、**シャドー AI のリスクを軽減**しています。企業が把握していない AI ツールの利用（シャドー AI）は、セキュリティリスクやコンプライアンス違反の原因となりますが、WitnessAI はこの課題に正面から取り組んでいます。

#### 2. 自動レッドチーミングと AI ファイアウォール

2025 年 8 月、WitnessAI は「Witness Attack」と「Witness Protect」という 2 つの新製品を発表しました。これらは、企業の大規模言語モデル（LLM）を脆弱性やリアルタイムの脅威から保護するための**自動レッドチーミングツールと AI ファイアウォール**として機能します。

従来、AI モデルのセキュリティテストは手動で行われることが多く、時間とコストがかかっていました。WitnessAI の自動化されたアプローチにより、**継続的なセキュリティ監視と保護**が可能となり、企業の AI 活用を安全に加速させることができます。

#### 3. 業界での評価と成長

2025 年 10 月、WitnessAI は Fortune 誌と Lightspeed Ventures が選出する「Fortune Cyber 60」リストに名を連ねました。これは、サイバーセキュリティ分野で最も成長し、価値を提供しているベンチャー企業を称えるリストであり、**WitnessAI の AI セキュリティ分野での革新性と成長**が評価された結果です。

企業が AI を本格導入する際、ガバナンスとセキュリティは不可欠な要素です。WitnessAI は、この課題に対する包括的なソリューションを提供することで、**企業の AI 活用を安全に支援するリーダー企業**としての地位を確立しつつあります。

**参考文献**

1. **Secure AI Enablement Platform の商用提供開始**
   - [WitnessAI Releases Secure Enablement Platform for AI - WitnessAI](https://witness.ai/resources/witnessai-releases-secure-enablement-platform-for-ai/)

2. **Fortune Cyber 60 リストへの選出**
   - [WitnessAI Named to Fortune Cyber 60 List - WitnessAI](https://witness.ai/resources/witnessai-named-to-fortune-cyber-60-list-as-business-momentum-accelerates/)

3. **新製品「Witness Attack」と「Witness Protect」**
   - [WitnessAI Launches Red-Teaming and AI Firewall Tools - Channel Insider](https://www.channelinsider.com/ai/witness-ai-security-enterprise-llm/)

4. **Microsoft Copilot との統合**
   - [WitnessAI Announces Support for Microsoft Copilot to Control Shadow AI - CIOFirst](https://ciofirst.com/witnessai-announces-support-for-microsoft-copilot-to-control-shadow-ai/)

---

## 9. Writer

**※2025年にも選出されており、2年連続で選ばれています。**

Writer は企業向け生成 AI プラットフォームです。

CRN では、汎用 AI をそのまま使うのではなく、

- 社内データ
- 企業ルール
- ブランドトーン

を前提にした AI 活用を可能にしている点が評価されています。

「とりあえず ChatGPT」から一歩進み、**企業専用 AI** をどう作るか、という文脈の代表例です。

**注目のポイント**

#### 1. 企業専用 AI の実現に向けた RAG 技術の強化

Writer は、データポイント間の意味的な関係をグラフ化する**高度な RAG（Retrieval-Augmented Generation）技術**を導入し、情報検索の精度と関連性を向上させています。これにより、企業が自社データを活用して AI システムと対話する際の**信頼性と関連性**が大幅に向上しています。

従来の RAG は、単純なベクトル検索に依存することが多く、文脈の理解が不十分でした。Writer のグラフ化アプローチにより、**データ間の意味的な関係を理解**し、より精度の高い情報検索と生成が可能になっています。

#### 2. 大規模データの処理能力強化

Writer は、最大**1,000 万語の企業固有情報**を処理・分析できるようになり、企業が自社データを活用して AI システムと対話する際のスケールが飛躍的に拡大しました。これにより、企業はより多くの情報を AI システムに統合し、**包括的な分析や洞察**を得ることができます。

「とりあえず ChatGPT」から一歩進み、企業専用 AI を実現するためには、企業の膨大なデータを扱えることが不可欠です。Writer の大規模データ処理能力は、**企業の全データ資産を活用した AI 活用**を可能にする重要な基盤となっています。

#### 3. 社内データ・企業ルール・ブランドトーンの統合

Writer は、社内データ、企業ルール、ブランドトーンを前提にした AI 活用を可能にしています。これは、単なる汎用 AI のカスタマイズではなく、**企業の文脈を深く理解した AI プラットフォーム**を提供することを意味します。

企業が AI を本格導入する際、ブランドトーンや企業ルールに沿ったコンテンツ生成は重要な要件です。Writer は、これらの要件を最初から考慮した設計により、**企業の一貫性を保ちながら AI を活用**できる環境を提供しています。

**参考文献**

1. **Writer プラットフォームの概要**
   - [Writer - Enterprise AI Platform](https://writer.com/)

2. **Writer の企業評価額と資金調達**
   - [AI Startup Writer Nabs A $1.9 Billion Valuation To Become A Super App For Enterprises - Forbes](https://www.forbes.com/sites/rashishrivastava/2024/11/12/ai-startup-writer-nabs-a-19-billion-valuation-to-become-a-super-app-for-enterprises/)

3. **Writer の企業情報**
   - [Writer | Company Overview & News - Forbes](https://www.forbes.com/companies/writer/)

---

## 10. DevRev

**※2025年にも選出されており、2年連続で選ばれています。**

DevRev は AI ネイティブなプラットフォームを提供する企業です。会話型 AI アシスタント「Computer」を特徴としており、顧客、プロダクト、エンジニアリングデータを統合します。

CRN では、Palo Alto に本拠を置く同社のプラットフォームが、データサイロの解消、手動タスクの自動化、チーム間のコラボレーション強化を目指している点が紹介されています。

既存のツール（Salesforce や Zendesk など）から構造化データと非構造化データを取得し、  
それをナレッジグラフに整理することで、会話型エンタープライズ AI を実現しています。

また、DevRev の新製品「Computer Agent Studio」は、エージェント構築をすべてのユーザーにアクセス可能にし、ノーコード、ローコード、フルコードのオプションを提供しています。

データサイロが解消され、手動タスクが自動化されることで、**チーム間のコラボレーションが強化**され、企業活動全体の効率化が実現される点が評価されています。

**注目のポイント**

#### 1. Computer Agent Studio によるエージェント構築の民主化

CRN 記事でも触れられている「Computer Agent Studio」は、エージェント構築をすべてのユーザーにアクセス可能にする重要な機能です。ノーコード、ローコード、フルコードのオプションを提供することで、**技術者だけでなく、ビジネスユーザーもエージェントを構築できる**環境を実現しています。

2025 年 10 月には、ニューヨークで「Effortless 2025」というイベントを開催し、Computer の進化を披露しました。このイベントでは、Vinod Khosla 氏（Khosla Ventures）や Dev Ittycheria 氏（MongoDB CEO）などの業界リーダーが参加し、Computer の新機能や企業での導入事例が紹介されました。

Computer Agent Studio は、**統合的な会話型コンピューティングの時代**を切り開く存在として位置づけられており、人間と機械が協働する新しい形を実現しようとしています。

#### 2. 日本市場への本格参入と国内企業との連携

2025 年 9 月、DevRev は日本法人「DevRev Japan 合同会社」を設立し、日本市場への本格参入を発表しました。コクヨ株式会社、北銀ソフトウェア株式会社、株式会社マクニカなどが初期導入企業として名を連ねています。

また、日本市場での展開を加速するため、クラスメソッド株式会社や Synthesy 株式会社との販売パートナー契約を締結しています。これらの動きは、**日本企業のニーズに応じた展開**を本格化させる戦略的取り組みです。

#### 3. AWS re:Invent 2025 での事例発表

AWS re:Invent 2025 において、Amazon OpenSearch の PM が実施したセッションで、DevRev が事例として発表されました。これは、DevRev のプラットフォームが**大規模なエンタープライズ環境での実運用**において、Amazon OpenSearch を活用した実績があることを示しています。

ナレッジグラフを中核とした DevRev のプラットフォームは、構造化データと非構造化データを統合する際に、検索機能が重要な役割を果たしています。Amazon OpenSearch との連携により、**大規模なデータセットに対する高速な検索と分析**が可能になっていると考えられます。

#### 4. 資金調達と評価額の成長

2024 年 11 月、DevRev はシリーズ A ラウンドで**1 億 800 万ドルを調達**し、評価額は**11 億 5000 万ドル**に達しました。これは、同社の AI Agent OS プラットフォームに対する市場の期待の高さを示しています。

Nutanix の創業者であるディラージ・パンディ氏と元 Nutanix エンジニアリング担当 SVP のマノージ・アガルワル氏によって設立された DevRev は、**エンタープライズソフトウェアの経験を活かした AI プラットフォーム**を提供しています。

**参考文献**

1. **Computer プラットフォームの発表**
   - [DevRev Launches Computer: The Conversational AI Teammate - Business Wire](https://www.businesswire.com/news/home/20250909035685/en/DevRev-Launches-Computer-The-Conversational-AI-Teammate-That-Redefines-How-Humans-and-Machines-Work-Together)

2. **Effortless 2025 イベント**
   - [DevRev Ushers in the Era of Integrated Conversational Computing at Effortless 2025 - Business Wire](https://www.businesswire.com/news/home/20251030127007/en/DevRev-Ushers-in-the-Era-of-Integrated-Conversational-Computing-at-Effortless-2025)

3. **日本法人の設立**
   - [DevRev、日本法人を設立 ～ AI エージェントの導入事例および国内パートナーとの AI における協業を発表～ - PR TIMES](https://prtimes.jp/main/html/rd/p/000000002.000171719.html)

4. **資金調達と評価額**
   - [DevRev Becomes AI Unicorn After Raising $100.8 Million in Series A - NextUnicorn Ventures](https://nextunicorn.ventures/devrev-becomes-ai-unicorn-after-raising-100-8-million-in-series-a/)

---

## おわりに

CRN のこのリストを見ると、2026 年に向けた AI の主戦場が **モデル性能そのものから、運用・記憶・権限・業務実行** へ移っていることがよく分かります。

「賢い AI を作る」だけでなく、**AI が働き続けられる環境をどう作るか**が問われるフェーズに入っています。モデル自体を改善する企業、セキュリティ企業、企業向けエージェントプラットフォーム企業が注目されています。

今後 1 年で、2025 年までは実現不可能だと思われていた企業内での AI 活用が一気に普及し、AI 格差も広がっていくと考えられます。エンジニア以外の職種も AI を活用できる環境を提供する組織が、いち早く企業として成長する世界が待っていると筆者は感じています。
