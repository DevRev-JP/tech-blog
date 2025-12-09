/**
 * SQL（値レイヤ）の最小構成例
 * 
 * 記事「LLM/RAG の曖昧性を抑える『形式レイヤ』の実装ガイド」の
 * ハンズオンセクション「最小構成の SQL 実装」に対応する例です。
 * 
 * ポイント：
 * - LLM は BillingQuery 型だけ返し、SQL はアプリ側で安全に決定します。
 * - パラメータ化クエリを使用することで、SQL インジェクションを防止します。
 */

import Database from "better-sqlite3";

type BillingQuery = {
  customerId: string;
  mode: "open" | "all";
};

const db = new Database("billing.db");

function runQuery(q: BillingQuery) {
  if (q.mode === "open") {
    return db
      .prepare(
        "SELECT id, amount, status FROM billing WHERE customer_id = ? AND status='open'"
      )
      .all(q.customerId);
  }
  return db
    .prepare("SELECT id, amount, status FROM billing WHERE customer_id = ?")
    .all(q.customerId);
}

// サンプル実行
const fromLlm: BillingQuery = { customerId: "CUST-123", mode: "open" };
console.log("Query:", fromLlm);
console.log("Results:", runQuery(fromLlm));

