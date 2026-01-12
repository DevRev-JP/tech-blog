# Git Push & PR ワークフロー

## Phase 1: Feature ブランチのプッシュと PR 作成

### 1. 現在のブランチを確認

```bash
git branch
```

### 2. Feature ブランチをリモートにプッシュ

```bash
# Feature ブランチにいることを確認後
git push origin feature/feature-name
```

### 3. Develop ブランチへの PR を作成

```bash
gh pr create --base develop --head feature/feature-name --title "PRタイトル" --body "PR説明"
```

**注意**: Develop へのマージは履歴を細かく残す（通常のマージコミットを使用）

---

## Phase 2: Develop へのマージ後処理

### 4. ローカルの Develop を更新

```bash
git checkout develop
git pull origin develop
```

### 5. リモートの Feature ブランチを削除

```bash
git push origin --delete feature/feature-name
```

### 6. ローカルの Feature ブランチを削除（オプション）

```bash
git branch -d feature/feature-name
```

---

## Phase 3: Main への PR 作成とマージ

### 7. Develop から Main への PR を作成

```bash
gh pr create --base main --head develop --title "Release: バージョン/説明" --body "リリース内容"
```

**注意**: Main へのマージ時は不要な履歴を残さない（Squash マージまたは Rebase マージを検討）

### 8. ローカルの Main を更新

```bash
git checkout main
git pull origin main
```

---

## Phase 4: 同期確認

### 9. 完全な同期を確認

```bash
# すべてのブランチの状態を確認
git fetch --all
git branch -a

# ローカルとリモートの差分を確認
git status
git log --oneline --graph --all --decorate
```
