#!/usr/bin/env python3
"""
統合ループシステム実行スクリプト
WEBアプリケーションの自動化テストループを実行
"""

import os
import sys
import asyncio
import argparse
import json
from datetime import datetime
from pathlib import Path
import subprocess
import signal
import time
import threading
from typing import Dict, Any, List

# システムパスの設定
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from loop_system import LoopSystemConfig, LoopController
from system_integration import EnhancedLoopController, WebAppChecker

class IntegratedLoopSystem:
    """統合ループシステム"""
    
    def __init__(self, config: LoopSystemConfig):
        self.config = config
        self.controller = None
        self.test_apps_process = None
        self.ollama_required = True
    
    async def run_complete_loop(self, target_url: str, auto_start_apps: bool = True) -> Dict[str, Any]:
        """完全なループシステムを実行"""
        print("🚀 統合ループシステム開始")
        print(f"対象URL: {target_url}")
        print(f"最大ループ回数: {self.config.max_loops}")
        print("=" * 60)
        
        try:
            # Step 1: 前提条件チェック
            await self._check_prerequisites()
            
            # Step 2: 必要に応じてテストアプリを起動
            if auto_start_apps:
                await self._start_test_applications()
            
            # Step 3: システム連携確認
            await self._verify_system_integration()
            
            # Step 4: 統合ループ制御システム初期化
            self.controller = EnhancedLoopController(self.config)
            
            # Step 5: メインループ実行
            loop_results = await self._execute_main_loop(target_url)
            
            # Step 6: 結果サマリー表示
            await self._display_final_summary(loop_results)
            
            return loop_results
            
        except KeyboardInterrupt:
            print("\n🛑 ユーザーによって中断されました")
            return {"cancelled": True}
        except Exception as e:
            print(f"\n❌ システムエラー: {e}")
            return {"error": str(e)}
        finally:
            # クリーンアップ
            await self._cleanup()
    
    async def _check_prerequisites(self):
        """前提条件チェック"""
        print("🔍 前提条件チェック中...")
        
        # Python依存関係チェック
        required_packages = [
            ("requests", "requests"),
            ("beautifulsoup4", "bs4"),
            ("flask", "flask")
        ]
        missing_packages = []
        
        for display_name, import_name in required_packages:
            try:
                __import__(import_name)
            except ImportError:
                missing_packages.append(display_name)
        
        if missing_packages:
            print(f"⚠️ 不足しているパッケージ: {', '.join(missing_packages)}")
            print("以下のコマンドでインストールしてください:")
            print(f"pip install {' '.join(missing_packages)}")
            sys.exit(1)
        
        # Ollamaサーバーチェック（オプション）
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                print("✅ Ollamaサーバー接続OK")
                self.ollama_required = True
            else:
                raise Exception("Connection failed")
        except Exception:
            print("⚠️ Ollamaサーバーが利用できません（基本機能で続行）")
            self.ollama_required = False
        
        # ディレクトリ作成
        self.config.loops_dir.mkdir(exist_ok=True)
        
        print("✅ 前提条件チェック完了")
    
    async def _start_test_applications(self):
        """テストアプリケーションを起動"""
        print("🚀 テストアプリケーション起動中...")
        
        # まず現在の状態をチェック
        service_status = await WebAppChecker.check_all_services()
        
        test_design_running = service_status["test_design_app"]["available"]
        test_execution_running = service_status["test_execution_app"]["available"]
        
        if test_design_running and test_execution_running:
            print("✅ テストアプリケーションは既に起動しています")
            return
        
        # start_apps.py を使用して起動
        start_script = Path(__file__).parent / "start_apps.py"
        if start_script.exists():
            print("📝 start_apps.py を使用してアプリケーションを起動...")
            try:
                # バックグラウンドで起動
                self.test_apps_process = subprocess.Popen([
                    sys.executable, str(start_script)
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # 起動を待機
                print("⏳ アプリケーション起動を待機中...")
                max_wait = 30  # 30秒待機
                for i in range(max_wait):
                    await asyncio.sleep(1)
                    service_status = await WebAppChecker.check_all_services()
                    
                    if (service_status["test_design_app"]["available"] and 
                        service_status["test_execution_app"]["available"]):
                        print("✅ テストアプリケーション起動完了")
                        return
                
                print("⚠️ アプリケーション起動タイムアウト（基本機能で続行）")
                
            except Exception as e:
                print(f"⚠️ アプリケーション起動エラー: {e}（基本機能で続行）")
        else:
            print("⚠️ start_apps.py が見つかりません（基本機能で続行）")
    
    async def _verify_system_integration(self):
        """システム統合確認"""
        print("🔗 システム統合確認中...")
        
        service_status = await WebAppChecker.check_all_services()
        
        integration_level = "full"
        
        if not service_status["test_design_app"]["available"]:
            print("⚠️ テスト設計アプリが利用できません")
            integration_level = "partial"
        
        if not service_status["test_execution_app"]["available"]:
            print("⚠️ テスト実行アプリが利用できません") 
            integration_level = "partial"
        
        if not self.ollama_required:
            print("⚠️ Ollamaが利用できません")
            integration_level = "basic"
        
        integration_names = {
            "full": "フル統合モード",
            "partial": "部分統合モード", 
            "basic": "基本モード"
        }
        
        print(f"📊 統合レベル: {integration_names[integration_level]}")
        return integration_level
    
    async def _execute_main_loop(self, target_url: str) -> Dict[str, Any]:
        """メインループ実行"""
        print("\n🔄 メインループ実行開始")
        
        current_loop = 0
        loop_results = []
        
        while current_loop < self.config.max_loops:
            current_loop += 1
            
            print(f"\n{'='*20} ループ {current_loop} {'='*20}")
            
            # ループディレクトリ作成
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            loop_dir = self.config.loops_dir / f"loop-{current_loop:03d}_{timestamp}"
            loop_dir.mkdir(parents=True, exist_ok=True)
            (loop_dir / "evidence").mkdir(exist_ok=True)
            
            try:
                # STEP 1: 仕様抽出
                print("📝 STEP 1: WEBアプリ仕様抽出")
                spec_result = await self.controller.spec_extractor.extract_specifications(target_url)
                self._save_json(loop_dir / "spec_extraction.json", spec_result)
                
                # 仕様書Markdown保存
                with open(loop_dir / "requirements.md", 'w', encoding='utf-8') as f:
                    f.write(spec_result.get("specification_document", ""))
                
                print(f"   ✅ 仕様抽出完了: {len(spec_result.get('ui_components', []))} UI要素検出")
                
                # STEP 2: テスト設計
                print("🔧 STEP 2: マルチエージェントテスト設計")
                test_design_result = await self.controller.run_integrated_test_design(spec_result, loop_dir)
                self._save_json(loop_dir / "test_design_result.json", test_design_result)
                
                test_cases_count = test_design_result.get("test_cases_count", 0)
                fallback = "（代替処理）" if test_design_result.get("fallback_used") else ""
                print(f"   ✅ テスト設計完了: {test_cases_count} テストケース生成{fallback}")
                
                # STEP 3: テスト実行
                print("▶️ STEP 3: テスト実行とエビデンス収集")
                test_execution_result = await self.controller.run_integrated_test_execution(test_design_result, loop_dir)
                self._save_json(loop_dir / "execution_results.json", test_execution_result)
                
                total = test_execution_result.get("total_tests", 0)
                passed = test_execution_result.get("passed_tests", 0)
                failed = test_execution_result.get("failed_tests", 0)
                fallback = "（代替処理）" if test_execution_result.get("fallback_used") else ""
                print(f"   ✅ テスト実行完了: {total}件実行, {passed}件成功, {failed}件失敗{fallback}")
                
                # STEP 4: 改善分析
                print("📊 STEP 4: 改善点分析")
                previous_data = loop_results[-1] if loop_results else None
                improvement_result = await self.controller.improvement_analyzer.analyze_improvements(
                    test_execution_result, previous_data
                )
                self._save_json(loop_dir / "improvement_analysis.json", improvement_result)
                
                improvements_count = len(improvement_result.get("improvement_suggestions", []))
                print(f"   ✅ 改善分析完了: {improvements_count}件の改善提案")
                
                # ループ結果記録
                loop_result = {
                    "loop_number": current_loop,
                    "loop_directory": str(loop_dir),
                    "target_url": target_url,
                    "spec_extraction": spec_result,
                    "test_design": test_design_result,
                    "test_execution": test_execution_result,
                    "improvement_analysis": improvement_result,
                    "timestamp": datetime.now().isoformat()
                }
                
                loop_results.append(loop_result)
                
                # 継続判定
                failed_tests = improvement_result.get("failed_tests", [])
                if len(failed_tests) == 0 and improvements_count <= 1:
                    print(f"🎉 改善目標達成！ループを終了します。")
                    break
                
                if current_loop < self.config.max_loops:
                    print(f"🔄 次のループに進みます...")
                    await asyncio.sleep(2)  # 短い休憩
                
            except Exception as e:
                print(f"❌ ループ {current_loop} でエラー: {e}")
                break
        
        # 最終レポート生成
        final_report = self._generate_final_report(loop_results, target_url)
        self._save_final_report(final_report)
        
        return {
            "total_loops_executed": len(loop_results),
            "loop_results": loop_results,
            "final_report": final_report,
            "target_url": target_url
        }
    
    async def _display_final_summary(self, loop_results: Dict[str, Any]):
        """最終サマリー表示"""
        print("\n" + "="*60)
        print("🎯 最終結果サマリー")
        print("="*60)
        
        total_loops = loop_results.get("total_loops_executed", 0)
        target_url = loop_results.get("target_url", "不明")
        
        print(f"対象URL: {target_url}")
        print(f"実行ループ数: {total_loops}")
        
        if "loop_results" in loop_results:
            # 各ループの統計
            total_tests = 0
            total_failures = 0
            
            for i, loop_result in enumerate(loop_results["loop_results"], 1):
                execution = loop_result.get("test_execution", {})
                tests = execution.get("total_tests", 0)
                failures = execution.get("failed_tests", 0)
                
                total_tests += tests
                total_failures += failures
                
                print(f"ループ {i}: {tests}テスト実行, {failures}件失敗")
            
            print(f"\n累計統計:")
            print(f"  総テスト数: {total_tests}")
            print(f"  総失敗数: {total_failures}")
            
            if total_tests > 0:
                success_rate = ((total_tests - total_failures) / total_tests) * 100
                print(f"  成功率: {success_rate:.1f}%")
        
        # 最終レポートの場所
        final_report = loop_results.get("final_report", {})
        report_timestamp = final_report.get("generated_at", datetime.now().isoformat())
        timestamp_str = report_timestamp.split("T")[0].replace("-", "")
        print(f"\n📄 詳細レポート: final_report_{timestamp_str}.json")
        print(f"📁 ループデータ: {self.config.loops_dir}")
        
        print("\n🎉 ループシステム実行完了!")
    
    def _save_json(self, filepath: Path, data: Dict):
        """JSONファイル保存"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _generate_final_report(self, loop_results: List[Dict], target_url: str) -> Dict[str, Any]:
        """最終レポート生成"""
        total_tests = sum(
            result.get("test_execution", {}).get("total_tests", 0) 
            for result in loop_results
        )
        total_failures = sum(
            len(result.get("improvement_analysis", {}).get("failed_tests", []))
            for result in loop_results
        )
        
        return {
            "target_url": target_url,
            "execution_summary": {
                "total_loops_executed": len(loop_results),
                "total_tests_run": total_tests,
                "total_failures_identified": total_failures,
                "success_rate": ((total_tests - total_failures) / total_tests * 100) if total_tests > 0 else 0
            },
            "improvement_summary": {
                "total_improvements_suggested": sum(
                    len(result.get("improvement_analysis", {}).get("improvement_suggestions", []))
                    for result in loop_results
                ),
                "final_loop_failures": len(loop_results[-1].get("improvement_analysis", {}).get("failed_tests", [])) if loop_results else 0
            },
            "recommendations": self._generate_recommendations(loop_results),
            "generated_at": datetime.now().isoformat(),
            "system_config": {
                "max_loops": self.config.max_loops,
                "ollama_available": self.ollama_required
            }
        }
    
    def _generate_recommendations(self, loop_results: List[Dict]) -> List[str]:
        """推奨事項生成"""
        if not loop_results:
            return ["データが不足しているため、推奨事項を生成できませんでした。"]
        
        latest_improvements = loop_results[-1].get("improvement_analysis", {}).get("improvement_suggestions", [])
        
        recommendations = []
        for improvement in latest_improvements[:3]:  # 上位3つ
            category = improvement.get("category", "一般")
            description = improvement.get("description", "")
            recommendations.append(f"{category}: {description}")
        
        if not recommendations:
            recommendations.append("システムは安定しており、継続的な監視を推奨します。")
        
        return recommendations
    
    def _save_final_report(self, final_report: Dict):
        """最終レポート保存"""
        timestamp = datetime.now().strftime("%Y%m%d")
        report_path = self.config.base_dir / f"final_report_{timestamp}.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(final_report, f, ensure_ascii=False, indent=2)
        
        print(f"📄 最終レポート保存: {report_path}")
    
    async def _cleanup(self):
        """クリーンアップ処理"""
        if self.test_apps_process and self.test_apps_process.poll() is None:
            print("🧹 テストアプリケーションを終了中...")
            self.test_apps_process.terminate()
            try:
                self.test_apps_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.test_apps_process.kill()

def main():
    """メイン実行関数"""
    parser = argparse.ArgumentParser(
        description="統合ループシステム - WEBアプリケーション自動化テスト",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  python run_loop_system.py --url https://example.com
  python run_loop_system.py --url https://example.com --max-loops 3
  python run_loop_system.py --url https://example.com --no-auto-start
        """
    )
    
    parser.add_argument(
        "--url", "-u", 
        required=True,
        help="対象WEBアプリケーションのURL"
    )
    parser.add_argument(
        "--max-loops", "-m", 
        type=int, 
        default=5,
        help="最大ループ回数 (デフォルト: 5)"
    )
    parser.add_argument(
        "--no-auto-start",
        action="store_true",
        help="テストアプリケーションの自動起動を無効にする"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true", 
        help="詳細ログを表示"
    )
    
    args = parser.parse_args()
    
    # 設定初期化
    config = LoopSystemConfig()
    config.max_loops = args.max_loops
    
    # システム初期化
    system = IntegratedLoopSystem(config)
    
    # 非同期実行
    try:
        result = asyncio.run(system.run_complete_loop(
            target_url=args.url,
            auto_start_apps=not args.no_auto_start
        ))
        
        if result.get("cancelled"):
            print("処理がキャンセルされました")
            sys.exit(1)
        elif result.get("error"):
            print(f"エラーが発生しました: {result['error']}")
            sys.exit(1)
        else:
            print("処理が正常に完了しました")
            sys.exit(0)
            
    except KeyboardInterrupt:
        print("\n\n🛑 ユーザーによって中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 予期しないエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()