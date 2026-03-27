# Tech Blog

このリポジトリは、[Zenn](https://zenn.dev/knowledge_graph) で公開している技術ブログの記事を管理しています。

主なテーマは **ナレッジグラフ（Knowledge Graph）** を中心とした AI 応用などの技術領域です。

記事はすべて Markdown 形式で執筆され、Zenn を通じて公開されています。  
最新の記事は以下からご覧いただけます。

👉 [https://zenn.dev/knowledge_graph](https://zenn.dev/knowledge_graph)

## ローカル開発

Zenn CLI はリポジトリの npm 依存としては管理していません。プレビューや記事生成は次のように **都度 `npx` で実行**してください（グローバルインストールでも可）。

```bash
npx zenn preview
npx zenn new:article --slug slug-name --title "タイトル" --type tech --emoji 🎯
```

参考文献 URL の検証スクリプトは `package.json` の `scripts` から実行できます。

```bash
npm run verify-urls
```

---

© DevRev Japan
