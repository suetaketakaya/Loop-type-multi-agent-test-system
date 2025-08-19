#!/usr/bin/env python3
"""
ループ型エージェント処理システム
WEBアプリケーション対象の自動化テストループ
「仕様書生成 → テスト設計 → テスト実行 → 改善点抽出 → 再ループ」
"""

import os
import json
import asyncio
import shutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import subprocess
import sys

# 既存システムのインポート
sys.path.append(os.path.join(os.path.dirname(__file__), 'multiagent'))
try:
    from multi_agent_system import MultiAgentSystem
    from config import config
    from ollama_client import OllamaClient
except ImportError:
    print("Warning: マルチエージェントシステムが見つかりません")
    MultiAgentSystem = None
    config = None
    OllamaClient = None

class LoopSystemConfig:
    """ループシステム設定"""
    def __init__(self):
        self.base_dir = Path(__file__).parent
        self.loops_dir = self.base_dir / "loops"
        self.templates_dir = self.base_dir / "templates"
        self.max_loops = 5  # 最大ループ回数
        self.ollama_models = {
            "spec_extraction": "llama3.2",
            "improvement_analysis": "llama3.2"
        }

class WebSpecExtractor:
    """WEBアプリケーション仕様抽出エージェント"""
    
    def __init__(self, ollama_client=None):
        self.ollama_client = ollama_client
    
    async def extract_specifications(self, target_url: str) -> Dict[str, Any]:
        """WEBアプリケーションから仕様を抽出"""
        try:
            # Step 1: HTMLコンテンツ取得
            html_content = await self._fetch_html_content(target_url)
            
            # Step 2: UIコンポーネント解析
            ui_components = await self._analyze_ui_components(html_content)
            
            # Step 3: 機能推定
            features = await self._estimate_features(html_content, ui_components, target_url)
            
            # Step 4: 仕様書生成
            spec_document = await self._generate_specification_document(
                target_url, html_content, ui_components, features
            )
            
            return {
                "target_url": target_url,
                "html_content": html_content,
                "ui_components": ui_components,
                "estimated_features": features,
                "specification_document": spec_document,
                "extraction_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"仕様抽出エラー: {e}")
            return self._create_fallback_spec(target_url)
    
    async def _fetch_html_content(self, url: str) -> str:
        """HTMLコンテンツを取得"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"HTML取得エラー: {e}")
            return f"<!-- HTML取得エラー: {e} -->"
    
    async def _analyze_ui_components(self, html_content: str) -> List[Dict[str, Any]]:
        """UIコンポーネントを解析"""
        soup = BeautifulSoup(html_content, 'html.parser')
        components = []
        
        # フォーム要素
        for form in soup.find_all('form'):
            components.append({
                "type": "form",
                "action": form.get('action', ''),
                "method": form.get('method', 'get'),
                "inputs": len(form.find_all('input')),
                "description": "フォーム要素"
            })
        
        # ナビゲーション
        for nav in soup.find_all('nav'):
            components.append({
                "type": "navigation",
                "links": len(nav.find_all('a')),
                "description": "ナビゲーション"
            })
        
        # ボタン
        buttons = soup.find_all(['button', 'input[type="submit"]', 'input[type="button"]'])
        for btn in buttons:
            components.append({
                "type": "button",
                "text": btn.get_text(strip=True) or btn.get('value', ''),
                "description": "ボタン要素"
            })
        
        # テーブル
        for table in soup.find_all('table'):
            components.append({
                "type": "table",
                "rows": len(table.find_all('tr')),
                "columns": len(table.find_all('th')) if table.find('th') else 0,
                "description": "テーブル要素"
            })
        
        return components
    
    async def _estimate_features(self, html_content: str, ui_components: List[Dict], url: str) -> List[Dict[str, Any]]:
        """機能を推定"""
        if not self.ollama_client:
            return self._create_fallback_features()
        
        prompt = f"""
以下のWEBアプリケーション情報から主要機能を推定してください。

URL: {url}

UIコンポーネント:
{json.dumps(ui_components, ensure_ascii=False, indent=2)}

HTMLスニペット (最初の1000文字):
{html_content[:1000]}

以下のJSON形式で回答してください:
{{
    "main_features": [
        {{
            "name": "機能名",
            "description": "機能説明",
            "category": "認証/データ管理/UI操作/その他",
            "priority": "高/中/低",
            "evidence": "推定根拠"
        }}
    ],
    "user_scenarios": [
        {{
            "scenario": "ユーザーシナリオ",
            "steps": ["ステップ1", "ステップ2"],
            "expected_outcome": "期待結果"
        }}
    ]
}}
"""
        
        try:
            response = await self.ollama_client.generate_response("llama3.2", prompt)
            # レスポンスがJSON文字列でない場合の処理
            if isinstance(response, str):
                try:
                    return json.loads(response)
                except json.JSONDecodeError:
                    print(f"機能推定エラー: レスポンスがJSONでありません")
                    return self._create_fallback_features()
            elif isinstance(response, dict):
                return response
            else:
                return self._create_fallback_features()
        except Exception as e:
            print(f"機能推定エラー: {e}")
            return self._create_fallback_features()
    
    async def _generate_specification_document(self, url: str, html_content: str, 
                                               ui_components: List, features: Dict) -> str:
        """仕様書ドキュメントを生成"""
        if not self.ollama_client:
            return self._create_fallback_spec_document(url)
        
        prompt = f"""
以下の情報から機能仕様書をMarkdown形式で作成してください。

対象URL: {url}
抽出日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

推定機能:
{json.dumps(features, ensure_ascii=False, indent=2)}

UIコンポーネント:
{json.dumps(ui_components, ensure_ascii=False, indent=2)}

以下の構成でMarkdown文書を作成してください:
# 機能仕様書

## 1. システム概要
## 2. 主要機能
## 3. ユーザーシナリオ
## 4. UI/UX要件
## 5. 技術要件
## 6. 品質要件
"""
        
        try:
            response = await self.ollama_client.generate_response("llama3.2", prompt)
            if isinstance(response, str):
                return response
            elif isinstance(response, dict) and 'content' in response:
                return response['content']
            else:
                return str(response)
        except Exception as e:
            print(f"仕様書生成エラー: {e}")
            return self._create_fallback_spec_document(url)
    
    def _create_fallback_spec(self, url: str) -> Dict[str, Any]:
        """フォールバック仕様"""
        return {
            "target_url": url,
            "html_content": "<!-- 取得できませんでした -->",
            "ui_components": [],
            "estimated_features": self._create_fallback_features(),
            "specification_document": self._create_fallback_spec_document(url),
            "extraction_timestamp": datetime.now().isoformat()
        }
    
    def _create_fallback_features(self) -> Dict[str, Any]:
        """フォールバック機能"""
        return {
            "main_features": [
                {
                    "name": "基本機能",
                    "description": "WEBアプリケーションの基本的な動作",
                    "category": "その他",
                    "priority": "高",
                    "evidence": "デフォルト機能"
                }
            ],
            "user_scenarios": [
                {
                    "scenario": "基本操作シナリオ",
                    "steps": ["サイトにアクセス", "基本操作を実行"],
                    "expected_outcome": "正常に動作すること"
                }
            ]
        }
    
    def _create_fallback_spec_document(self, url: str) -> str:
        """フォールバック仕様書"""
        return f"""# 機能仕様書

## 1. システム概要
対象URL: {url}
抽出日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 2. 主要機能
- 基本的なWEBアプリケーション機能

## 3. ユーザーシナリオ
- ユーザーがサイトにアクセスする
- 基本的な操作を行う

## 4. UI/UX要件
- 標準的なWEBユーザーインターフェース

## 5. 技術要件
- WEBブラウザ対応

## 6. 品質要件
- 安定した動作
- 適切なレスポンス時間
"""

class ImprovementAnalyzer:
    """改善点分析エージェント"""
    
    def __init__(self, ollama_client=None):
        self.ollama_client = ollama_client
    
    async def analyze_improvements(self, test_results: Dict[str, Any], 
                                   previous_loop_data: Optional[Dict] = None) -> Dict[str, Any]:
        """改善点を分析"""
        try:
            # Step 1: テスト結果分析
            failed_tests = self._extract_failed_tests(test_results)
            
            # Step 2: エビデンス収集
            evidence = await self._collect_evidence(test_results, failed_tests)
            
            # Step 3: 改善提案生成
            improvements = await self._generate_improvements(failed_tests, evidence, previous_loop_data)
            
            # Step 4: 次回ループ計画
            next_loop_plan = await self._create_next_loop_plan(improvements)
            
            return {
                "failed_tests": failed_tests,
                "evidence": evidence,
                "improvement_suggestions": improvements,
                "next_loop_plan": next_loop_plan,
                "analysis_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"改善分析エラー: {e}")
            return self._create_fallback_improvement()
    
    def _extract_failed_tests(self, test_results: Dict) -> List[Dict]:
        """失敗テストを抽出"""
        failed_tests = []
        
        # テスト実行結果から失敗を抽出
        execution_results = test_results.get("execution_results", [])
        for execution in execution_results:
            if execution.get("status") in ["failed", "error"]:
                failed_tests.append({
                    "test_case_id": execution.get("test_case_id"),
                    "test_name": execution.get("test_name"),
                    "failure_reason": execution.get("failure_reason", "不明"),
                    "error_details": execution.get("error_details", [])
                })
        
        return failed_tests
    
    async def _collect_evidence(self, test_results: Dict, failed_tests: List) -> Dict[str, Any]:
        """エビデンスを収集"""
        evidence = {
            "screenshots": [],
            "logs": [],
            "performance_metrics": {},
            "error_traces": []
        }
        
        # テスト実行ログからエビデンス収集
        for execution in test_results.get("execution_results", []):
            if execution.get("screenshots"):
                evidence["screenshots"].extend(execution["screenshots"])
            
            if execution.get("logs"):
                evidence["logs"].extend(execution["logs"])
            
            if execution.get("error_traces"):
                evidence["error_traces"].extend(execution["error_traces"])
        
        return evidence
    
    async def _generate_improvements(self, failed_tests: List, evidence: Dict, 
                                     previous_data: Optional[Dict]) -> List[Dict]:
        """改善提案を生成"""
        if not self.ollama_client:
            return self._create_fallback_improvements(failed_tests)
        
        prompt = f"""
以下のテスト失敗結果とエビデンスから改善提案を作成してください。

失敗テスト:
{json.dumps(failed_tests, ensure_ascii=False, indent=2)}

エビデンス情報:
- スクリーンショット数: {len(evidence.get('screenshots', []))}
- ログ数: {len(evidence.get('logs', []))}
- エラートレース数: {len(evidence.get('error_traces', []))}

前回のループデータ:
{json.dumps(previous_data, ensure_ascii=False, indent=2) if previous_data else "初回ループ"}

以下のJSON形式で回答してください:
{{
    "improvements": [
        {{
            "category": "機能改善/性能改善/UI改善/セキュリティ改善",
            "priority": "高/中/低",
            "description": "改善内容の説明",
            "implementation_suggestion": "実装提案",
            "test_strategy": "テスト戦略"
        }}
    ],
    "root_causes": [
        {{
            "issue": "問題",
            "cause": "根本原因",
            "impact": "影響範囲"
        }}
    ]
}}
"""
        
        try:
            response = await self.ollama_client.generate_response("llama3.2", prompt)
            # レスポンスがJSON文字列でない場合の処理
            if isinstance(response, str):
                try:
                    result = json.loads(response)
                    return result.get("improvements", [])
                except json.JSONDecodeError:
                    print(f"改善提案生成エラー: レスポンスがJSONでありません")
                    return self._create_fallback_improvements(failed_tests)
            elif isinstance(response, dict):
                return response.get("improvements", [])
            else:
                return self._create_fallback_improvements(failed_tests)
        except Exception as e:
            print(f"改善提案生成エラー: {e}")
            return self._create_fallback_improvements(failed_tests)
    
    async def _create_next_loop_plan(self, improvements: List[Dict]) -> Dict[str, Any]:
        """次回ループ計画を作成"""
        return {
            "focus_areas": [imp["category"] for imp in improvements],
            "priority_improvements": [imp for imp in improvements if imp.get("priority") == "高"],
            "test_strategy_updates": [imp["test_strategy"] for imp in improvements if "test_strategy" in imp],
            "estimated_effort": "中" if len(improvements) <= 3 else "高"
        }
    
    def _create_fallback_improvements(self, failed_tests: List) -> List[Dict]:
        """フォールバック改善提案"""
        return [
            {
                "category": "機能改善",
                "priority": "高",
                "description": f"{len(failed_tests)}個のテスト失敗に対する基本的な改善",
                "implementation_suggestion": "テスト失敗の詳細を確認し、該当機能の修正を行う",
                "test_strategy": "失敗したテストケースを重点的に再テスト"
            }
        ]
    
    def _create_fallback_improvement(self) -> Dict[str, Any]:
        """フォールバック改善分析"""
        return {
            "failed_tests": [],
            "evidence": {"screenshots": [], "logs": [], "performance_metrics": {}, "error_traces": []},
            "improvement_suggestions": [],
            "next_loop_plan": {"focus_areas": [], "priority_improvements": []},
            "analysis_timestamp": datetime.now().isoformat()
        }

class LoopController:
    """ループ制御システム"""
    
    def __init__(self, config: LoopSystemConfig):
        self.config = config
        self.current_loop = 0
        self.target_url = None
        self.loop_history = []
        
        # 既存システムとの連携
        self.multi_agent_system = None
        if MultiAgentSystem:
            self.multi_agent_system = MultiAgentSystem()
        
        # エージェント初期化
        ollama_client = None
        if config and OllamaClient:
            try:
                ollama_client = OllamaClient(config.ollama if config else None)
            except:
                pass
        
        self.spec_extractor = WebSpecExtractor(ollama_client)
        self.improvement_analyzer = ImprovementAnalyzer(ollama_client)
    
    async def start_loop_process(self, target_url: str) -> Dict[str, Any]:
        """ループ処理を開始"""
        self.target_url = target_url
        self.current_loop = 0
        
        print(f"🔄 ループ処理開始: {target_url}")
        
        loop_results = []
        
        while self.current_loop < self.config.max_loops:
            self.current_loop += 1
            
            print(f"\n🔄 ===== ループ {self.current_loop} 開始 =====")
            
            # ループディレクトリ作成
            loop_dir = self._create_loop_directory(self.current_loop)
            
            try:
                # STEP 1: 仕様抽出
                print("📝 STEP 1: WEBアプリ仕様抽出")
                spec_result = await self.spec_extractor.extract_specifications(target_url)
                self._save_specification(loop_dir, spec_result)
                
                # STEP 2: テスト設計
                print("🔧 STEP 2: マルチエージェントテスト設計")
                test_design_result = await self._run_test_design(spec_result, loop_dir)
                
                # STEP 3: テスト実行
                print("▶️ STEP 3: テスト実行")
                test_execution_result = await self._run_test_execution(test_design_result, loop_dir)
                
                # STEP 4: 改善分析
                print("📊 STEP 4: 改善点分析")
                previous_data = self.loop_history[-1] if self.loop_history else None
                improvement_result = await self.improvement_analyzer.analyze_improvements(
                    test_execution_result, previous_data
                )
                self._save_improvement_analysis(loop_dir, improvement_result)
                
                # ループ結果記録
                loop_result = {
                    "loop_number": self.current_loop,
                    "loop_directory": str(loop_dir),
                    "spec_extraction": spec_result,
                    "test_design": test_design_result,
                    "test_execution": test_execution_result,
                    "improvement_analysis": improvement_result,
                    "timestamp": datetime.now().isoformat()
                }
                
                loop_results.append(loop_result)
                self.loop_history.append(loop_result)
                
                # 継続判定
                if self._should_continue_loop(improvement_result):
                    print(f"🔄 ループ {self.current_loop} 完了。次のループに進みます。")
                    await asyncio.sleep(2)  # 短い休憩
                else:
                    print(f"✅ 改善が十分達成されました。ループを終了します。")
                    break
                    
            except Exception as e:
                print(f"❌ ループ {self.current_loop} でエラー: {e}")
                break
        
        # 最終レポート生成
        final_report = self._generate_final_report(loop_results)
        self._save_final_report(final_report)
        
        print(f"\n🎉 ループ処理完了。合計 {len(loop_results)} ループを実行しました。")
        
        return {
            "total_loops": len(loop_results),
            "loop_results": loop_results,
            "final_report": final_report
        }
    
    def _create_loop_directory(self, loop_number: int) -> Path:
        """ループディレクトリを作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        loop_dir = self.config.loops_dir / f"loop-{loop_number:03d}_{timestamp}"
        loop_dir.mkdir(parents=True, exist_ok=True)
        
        # サブディレクトリ作成
        (loop_dir / "evidence").mkdir(exist_ok=True)
        (loop_dir / "test_results").mkdir(exist_ok=True)
        
        return loop_dir
    
    def _save_specification(self, loop_dir: Path, spec_result: Dict):
        """仕様書を保存"""
        # JSON形式で詳細保存
        with open(loop_dir / "spec_extraction.json", 'w', encoding='utf-8') as f:
            json.dump(spec_result, f, ensure_ascii=False, indent=2)
        
        # Markdown形式で仕様書保存
        with open(loop_dir / "requirements.md", 'w', encoding='utf-8') as f:
            f.write(spec_result.get("specification_document", ""))
    
    async def _run_test_design(self, spec_result: Dict, loop_dir: Path) -> Dict[str, Any]:
        """テスト設計実行"""
        # 既存のテスト設計アプリの機能を呼び出し
        # ここでは簡略化したダミー実装
        return {
            "test_cases_generated": 5,
            "requirements_analyzed": True,
            "design_completed": True,
            "test_cases": [
                {
                    "test_case_id": f"TC-{i:03d}",
                    "test_name": f"テストケース{i}",
                    "test_steps": ["ステップ1", "ステップ2"],
                    "expected_results": ["期待結果"]
                }
                for i in range(1, 6)
            ]
        }
    
    async def _run_test_execution(self, test_design_result: Dict, loop_dir: Path) -> Dict[str, Any]:
        """テスト実行"""
        # 既存のテスト実行アプリの機能を呼び出し
        # ここでは簡略化したダミー実装
        return {
            "execution_results": [
                {
                    "test_case_id": tc["test_case_id"],
                    "test_name": tc["test_name"],
                    "status": "passed" if i % 4 != 0 else "failed",  # 4つに1つは失敗
                    "failure_reason": "予期しない結果" if i % 4 == 0 else None
                }
                for i, tc in enumerate(test_design_result.get("test_cases", []), 1)
            ],
            "total_tests": len(test_design_result.get("test_cases", [])),
            "passed_tests": len([tc for i, tc in enumerate(test_design_result.get("test_cases", []), 1) if i % 4 != 0]),
            "failed_tests": len([tc for i, tc in enumerate(test_design_result.get("test_cases", []), 1) if i % 4 == 0])
        }
    
    def _save_improvement_analysis(self, loop_dir: Path, improvement_result: Dict):
        """改善分析を保存"""
        with open(loop_dir / "improvements.json", 'w', encoding='utf-8') as f:
            json.dump(improvement_result, f, ensure_ascii=False, indent=2)
    
    def _should_continue_loop(self, improvement_result: Dict) -> bool:
        """ループ継続判定"""
        failed_tests = improvement_result.get("failed_tests", [])
        
        # 失敗テストがなく、改善提案も少ない場合は終了
        if len(failed_tests) == 0 and len(improvement_result.get("improvement_suggestions", [])) <= 1:
            return False
        
        # 最大ループ数に達した場合は終了
        if self.current_loop >= self.config.max_loops:
            return False
        
        return True
    
    def _generate_final_report(self, loop_results: List[Dict]) -> Dict[str, Any]:
        """最終レポート生成"""
        total_tests = sum(result["test_execution"].get("total_tests", 0) for result in loop_results)
        total_failures = sum(len(result["improvement_analysis"].get("failed_tests", [])) for result in loop_results)
        
        return {
            "target_url": self.target_url,
            "total_loops_executed": len(loop_results),
            "total_tests_run": total_tests,
            "total_failures_identified": total_failures,
            "improvement_trend": self._analyze_improvement_trend(loop_results),
            "final_recommendations": self._generate_final_recommendations(loop_results),
            "generated_at": datetime.now().isoformat()
        }
    
    def _analyze_improvement_trend(self, loop_results: List[Dict]) -> Dict[str, Any]:
        """改善トレンドを分析"""
        failure_counts = [
            len(result["improvement_analysis"].get("failed_tests", []))
            for result in loop_results
        ]
        
        return {
            "failure_trend": failure_counts,
            "improvement_detected": failure_counts[-1] < failure_counts[0] if len(failure_counts) > 1 else False,
            "stability_achieved": failure_counts[-1] == 0 if failure_counts else False
        }
    
    def _generate_final_recommendations(self, loop_results: List[Dict]) -> List[str]:
        """最終推奨事項を生成"""
        recommendations = []
        
        # 最新の改善提案から推奨事項を抽出
        if loop_results:
            latest_improvements = loop_results[-1]["improvement_analysis"].get("improvement_suggestions", [])
            for imp in latest_improvements[:3]:  # 上位3つ
                recommendations.append(f"{imp.get('category', '一般')}改善: {imp.get('description', '')}")
        
        if not recommendations:
            recommendations.append("システムは概ね安定しており、継続的な監視を推奨します。")
        
        return recommendations
    
    def _save_final_report(self, final_report: Dict):
        """最終レポート保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = self.config.base_dir / f"final_report_{timestamp}.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, ensure_ascii=False, indent=2)
        
        print(f"📄 最終レポート保存: {report_path}")

async def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="ループ型エージェント処理システム")
    parser.add_argument("--url", "-u", required=True, help="対象WEBアプリケーションURL")
    parser.add_argument("--max-loops", "-m", type=int, default=5, help="最大ループ回数")
    
    args = parser.parse_args()
    
    # 設定初期化
    config = LoopSystemConfig()
    config.max_loops = args.max_loops
    
    # ループ制御システム初期化
    controller = LoopController(config)
    
    # ループ処理実行
    result = await controller.start_loop_process(args.url)
    
    print(f"\n🎯 処理完了:")
    print(f"   対象URL: {args.url}")
    print(f"   実行ループ数: {result['total_loops']}")
    print(f"   最終レポート: final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")

if __name__ == "__main__":
    asyncio.run(main())