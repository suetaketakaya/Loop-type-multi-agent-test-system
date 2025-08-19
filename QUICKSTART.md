# 🚀 クイックスタートガイド

## ループ型エージェント処理システム

既存のWebアプリケーションに対して「仕様書生成 → テスト設計 → テスト実行 → 改善点とエビデンス収集 → 再ループ」を自動化するシステムです。

## 📋 システム構成

```
multiagent_testdoc/
├── 🔄 ループシステム (新規作成)
│   ├── loop_system.py           # コアループシステム
│   ├── system_integration.py    # 既存システム統合
│   └── run_loop_system.py       # メイン実行スクリプト
├── 🏗️ 既存システム
│   ├── multiagent/              # マルチエージェント基盤
│   ├── test_design_app/         # テスト設計アプリ (ポート5003)
│   ├── test_execution_app/      # テスト実行アプリ (ポート5001)
│   └── start_apps.py           # 既存アプリ起動スクリプト
└── 📊 出力結果
    ├── loops/                   # ループごとの詳細データ
    └── final_report_*.json      # 最終レポート
```

## 🛠️ セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. Ollamaサーバーの起動（推奨）

```bash
# Ollamaをインストール（まだの場合）
# https://ollama.ai/download

# Ollamaサーバーを起動
ollama serve

# 必要なモデルをダウンロード
ollama pull llama3.2
```

**注意**: Ollamaが利用できない場合も基本機能で動作します

## 🎯 使用方法

### 基本使用例

```bash
# 最もシンプルな実行
python run_loop_system.py --url https://example.com

# ループ回数を指定
python run_loop_system.py --url https://example.com --max-loops 3

# テストアプリの自動起動を無効化（手動で起動済みの場合）
python run_loop_system.py --url https://example.com --no-auto-start
```

### 詳細オプション

```bash
python run_loop_system.py \
  --url https://your-webapp.com \
  --max-loops 5 \
  --verbose
```

### パラメーター説明

- `--url` (必須): 対象WEBアプリケーションのURL
- `--max-loops`: 最大ループ回数 (デフォルト: 5)
- `--no-auto-start`: テストアプリの自動起動を無効化
- `--verbose`: 詳細ログを表示

## 📊 出力結果

### ループディレクトリ構造

```
loops/loop-001_20250819_143022/
├── requirements.md              # 抽出された仕様書
├── spec_extraction.json        # 仕様抽出詳細データ
├── test_design_result.json     # テスト設計結果
├── test_cases.csv              # 生成されたテストケース
├── execution_results.json      # テスト実行結果
├── improvement_analysis.json   # 改善分析結果
└── evidence/                   # エビデンス（スクショ、ログ等）
```

### 最終レポート

`final_report_YYYYMMDD.json` - 全ループの統計とサマリー

## 🔄 処理フロー

### 各ループの実行ステップ

1. **🌐 STEP 1: WEBアプリ仕様抽出**
   - 対象URLからHTMLを取得
   - UIコンポーネントを解析
   - 機能要件を推定
   - 仕様書(Markdown)を生成

2. **🔧 STEP 2: マルチエージェントテスト設計**
   - 既存テスト設計アプリと連携
   - 4つのエージェント（要求分析、テスト設計、品質保証、リスク分析）
   - テストケースをCSV出力

3. **▶️ STEP 3: テスト実行とエビデンス収集**
   - 既存テスト実行アプリと連携
   - 人間介入型テスト実行
   - エビデンス（スクショ、ログ）収集

4. **📊 STEP 4: 改善点分析**
   - テスト失敗要因を分析
   - エビデンスベースの改善提案
   - 次ループの計画策定

### ループ継続条件

- 失敗テストが存在する
- 重要な改善提案がある
- 最大ループ回数に未到達

### 終了条件

- 全テストが成功
- 改善提案が少ない（1個以下）
- 最大ループ回数に到達

## 🧪 テスト実行

### システム統合テスト

```bash
# 統合テストの実行
python system_integration.py
```

### サンプル実行

```bash
# 公開サイトでテスト実行
python run_loop_system.py --url https://httpbin.org --max-loops 2

# ローカル開発サーバーでテスト
python run_loop_system.py --url http://localhost:3000
```

## 🔧 トラブルシューティング

### よくある問題

1. **Ollamaサーバーに接続できない**
   ```bash
   # Ollamaサーバーを再起動
   ollama serve
   ```

2. **テストアプリが起動しない**
   ```bash
   # 手動でアプリを起動
   python start_apps.py
   
   # ポートが使用中の場合、プロセスを終了
   lsof -ti:5001,5003 | xargs kill -9
   ```

3. **依存関係のエラー**
   ```bash
   # 依存関係を再インストール
   pip install --upgrade -r requirements.txt
   ```

4. **メモリ不足**
   ```bash
   # ループ数を削減
   python run_loop_system.py --url https://example.com --max-loops 2
   ```

### ログ確認

- 詳細ログが必要な場合は `--verbose` オプションを使用
- 各ループディレクトリに詳細なJSONログが保存される

## 📈 統合レベル

システムは3つの統合レベルで動作します：

1. **フル統合モード**
   - Ollama LLM + テスト設計アプリ + テスト実行アプリ
   - 最高品質の解析とテスト実行

2. **部分統合モード**
   - 一部のコンポーネントが利用できない場合
   - 利用可能な機能で処理を継続

3. **基本モード**
   - Ollamaとテストアプリが利用できない場合
   - 簡易的な仕様抽出とテスト実行

## 🎯 使用例とユースケース

### ユースケース1: 新機能リリース前の品質確認

```bash
python run_loop_system.py \
  --url https://staging.example.com/new-feature \
  --max-loops 3
```

### ユースケース2: 本番環境の継続的監視

```bash
python run_loop_system.py \
  --url https://production.example.com \
  --max-loops 5
```

### ユースケース3: 競合サイトの分析

```bash
python run_loop_system.py \
  --url https://competitor.com \
  --max-loops 2
```

## 📧 サポート

問題が発生した場合は、以下の情報と共にissueを作成してください：

- 実行したコマンド
- エラーメッセージ
- システム環境（OS、Python版）
- `final_report_*.json` の内容（可能な場合）

---

🎉 **Happy Testing!** このシステムを使用して、効率的なWebアプリケーション品質保証を実現しましょう。