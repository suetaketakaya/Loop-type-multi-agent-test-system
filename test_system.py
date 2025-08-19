#!/usr/bin/env python3
"""
システム動作確認・テストスクリプト
ループシステムの各コンポーネントをテスト
"""

import asyncio
import sys
import os
import json
import time
from pathlib import Path

# システムパス設定
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from loop_system import LoopSystemConfig, WebSpecExtractor, ImprovementAnalyzer
from system_integration import WebAppChecker, TestDesignIntegration, TestExecutionIntegration

class SystemTester:
    """システムテスター"""
    
    def __init__(self):
        self.test_results = {}
        self.config = LoopSystemConfig()
    
    async def run_all_tests(self):
        """全テストを実行"""
        print("🧪 システム動作確認テスト開始")
        print("=" * 50)
        
        tests = [
            ("基本設定確認", self.test_basic_config),
            ("依存関係確認", self.test_dependencies),
            ("Ollamaサーバー接続", self.test_ollama_connection),
            ("WEB仕様抽出", self.test_spec_extraction),
            ("改善分析", self.test_improvement_analysis),
            ("サービス状態確認", self.test_service_availability),
            ("ディレクトリ作成", self.test_directory_creation),
            ("統合コンポーネント", self.test_integration_components)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🔍 {test_name}...")
            try:
                result = await test_func()
                if result:
                    print(f"  ✅ {test_name}: 成功")
                    passed += 1
                else:
                    print(f"  ❌ {test_name}: 失敗")
                self.test_results[test_name] = result
            except Exception as e:
                print(f"  ❌ {test_name}: エラー - {e}")
                self.test_results[test_name] = False
        
        # サマリー表示
        print("\n" + "=" * 50)
        print(f"🎯 テスト結果: {passed}/{total} 成功")
        
        if passed == total:
            print("✅ 全テストが成功しました！システムは正常に動作します。")
        elif passed >= total * 0.7:
            print("⚠️ 一部の機能で問題がありますが、基本機能は利用できます。")
        else:
            print("❌ 複数の問題が検出されました。設定を確認してください。")
        
        # 詳細結果保存
        await self.save_test_results()
        
        return passed, total
    
    async def test_basic_config(self) -> bool:
        """基本設定確認"""
        try:
            # 設定ファイルの確認
            config_valid = (
                hasattr(self.config, 'base_dir') and
                hasattr(self.config, 'loops_dir') and
                hasattr(self.config, 'max_loops')
            )
            
            if not config_valid:
                return False
            
            # ディレクトリの存在確認
            self.config.loops_dir.mkdir(parents=True, exist_ok=True)
            
            return self.config.loops_dir.exists()
            
        except Exception as e:
            print(f"    設定エラー: {e}")
            return False
    
    async def test_dependencies(self) -> bool:
        """依存関係確認"""
        required_modules = [
            ('requests', 'requests'),
            ('beautifulsoup4', 'bs4'), 
            ('flask', 'flask'),
            ('pathlib', 'pathlib'),
            ('json', 'json'),
            ('datetime', 'datetime')
        ]
        
        missing = []
        for display_name, import_name in required_modules:
            try:
                __import__(import_name)
            except ImportError:
                missing.append(display_name)
        
        if missing:
            print(f"    不足モジュール: {', '.join(missing)}")
            return False
        
        return True
    
    async def test_ollama_connection(self) -> bool:
        """Ollama接続テスト"""
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            
            if response.status_code == 200:
                models = response.json().get('models', [])
                print(f"    利用可能モデル: {len(models)}個")
                return True
            else:
                print(f"    Ollamaサーバー応答エラー: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"    Ollama接続エラー: {e}")
            print("    注意: Ollamaなしでも基本機能は利用できます")
            return False
    
    async def test_spec_extraction(self) -> bool:
        """WEB仕様抽出テスト"""
        try:
            extractor = WebSpecExtractor()
            
            # テスト用の簡単なURL
            test_url = "https://httpbin.org/html"
            result = await extractor.extract_specifications(test_url)
            
            required_keys = ['target_url', 'html_content', 'ui_components', 'estimated_features']
            return all(key in result for key in required_keys)
            
        except Exception as e:
            print(f"    仕様抽出エラー: {e}")
            return False
    
    async def test_improvement_analysis(self) -> bool:
        """改善分析テスト"""
        try:
            analyzer = ImprovementAnalyzer()
            
            # テスト用のダミーデータ
            test_results = {
                "execution_results": [
                    {
                        "test_case_id": "TC-001",
                        "test_name": "テストケース1",
                        "status": "failed",
                        "failure_reason": "テスト失敗"
                    }
                ]
            }
            
            result = await analyzer.analyze_improvements(test_results)
            
            required_keys = ['failed_tests', 'evidence', 'improvement_suggestions', 'next_loop_plan']
            return all(key in result for key in required_keys)
            
        except Exception as e:
            print(f"    改善分析エラー: {e}")
            return False
    
    async def test_service_availability(self) -> bool:
        """サービス利用可能性テスト"""
        try:
            service_status = await WebAppChecker.check_all_services()
            
            test_design_available = service_status["test_design_app"]["available"]
            test_execution_available = service_status["test_execution_app"]["available"]
            
            if test_design_available and test_execution_available:
                print("    両方のテストアプリが利用可能")
                return True
            elif test_design_available or test_execution_available:
                print("    一部のテストアプリが利用可能")
                return True
            else:
                print("    テストアプリは利用できません（代替処理で動作）")
                return True  # 代替処理があるのでTrue
                
        except Exception as e:
            print(f"    サービス確認エラー: {e}")
            return False
    
    async def test_directory_creation(self) -> bool:
        """ディレクトリ作成テスト"""
        try:
            # テストディレクトリ作成
            test_dir = self.config.loops_dir / "test_loop_001"
            test_dir.mkdir(parents=True, exist_ok=True)
            
            # サブディレクトリ作成
            (test_dir / "evidence").mkdir(exist_ok=True)
            (test_dir / "test_results").mkdir(exist_ok=True)
            
            # ファイル作成テスト
            test_file = test_dir / "test.json"
            with open(test_file, 'w') as f:
                json.dump({"test": "data"}, f)
            
            success = test_dir.exists() and test_file.exists()
            
            # クリーンアップ
            import shutil
            if test_dir.exists():
                shutil.rmtree(test_dir)
            
            return success
            
        except Exception as e:
            print(f"    ディレクトリ作成エラー: {e}")
            return False
    
    async def test_integration_components(self) -> bool:
        """統合コンポーネントテスト"""
        try:
            # TestDesignIntegration テスト
            test_design = TestDesignIntegration()
            self.assertTrue(hasattr(test_design, 'app_url'))
            
            # TestExecutionIntegration テスト
            test_execution = TestExecutionIntegration()
            self.assertTrue(hasattr(test_execution, 'app_url'))
            
            return True
            
        except Exception as e:
            print(f"    統合コンポーネントエラー: {e}")
            return False
    
    def assertTrue(self, condition):
        """簡易アサート"""
        if not condition:
            raise AssertionError("条件が満たされません")
    
    async def save_test_results(self):
        """テスト結果保存"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_file = self.config.base_dir / f"test_results_{timestamp}.json"
        
        detailed_results = {
            "test_timestamp": timestamp,
            "system_info": {
                "python_version": sys.version,
                "platform": sys.platform
            },
            "test_results": self.test_results,
            "summary": {
                "total_tests": len(self.test_results),
                "passed_tests": sum(1 for r in self.test_results.values() if r),
                "failed_tests": sum(1 for r in self.test_results.values() if not r)
            }
        }
        
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(detailed_results, f, ensure_ascii=False, indent=2)
        
        print(f"📄 テスト結果保存: {results_file}")

async def quick_demo():
    """クイックデモ実行"""
    print("🎬 クイックデモ開始")
    print("=" * 30)
    
    # 基本機能のデモンストレーション
    config = LoopSystemConfig()
    
    print("1. 設定確認")
    print(f"   ベースディレクトリ: {config.base_dir}")
    print(f"   ループディレクトリ: {config.loops_dir}")
    print(f"   最大ループ回数: {config.max_loops}")
    
    print("\n2. 仕様抽出デモ")
    extractor = WebSpecExtractor()
    demo_result = await extractor.extract_specifications("https://httpbin.org")
    
    print(f"   対象URL: {demo_result['target_url']}")
    print(f"   UIコンポーネント数: {len(demo_result['ui_components'])}")
    print(f"   推定機能数: {len(demo_result['estimated_features'].get('main_features', []))}")
    
    print("\n3. 改善分析デモ")
    analyzer = ImprovementAnalyzer()
    demo_test_results = {
        "execution_results": [
            {"test_case_id": "TC-001", "status": "passed"},
            {"test_case_id": "TC-002", "status": "failed", "failure_reason": "タイムアウト"}
        ]
    }
    
    improvement_result = await analyzer.analyze_improvements(demo_test_results)
    print(f"   失敗テスト数: {len(improvement_result['failed_tests'])}")
    print(f"   改善提案数: {len(improvement_result['improvement_suggestions'])}")
    
    print("\n🎉 デモ完了！")

def main():
    """メイン実行"""
    import argparse
    
    parser = argparse.ArgumentParser(description="システムテスト・デモ実行")
    parser.add_argument("--demo", action="store_true", help="クイックデモを実行")
    parser.add_argument("--test", action="store_true", help="システムテストを実行")
    
    args = parser.parse_args()
    
    if args.demo:
        asyncio.run(quick_demo())
    elif args.test:
        tester = SystemTester()
        asyncio.run(tester.run_all_tests())
    else:
        print("オプションを指定してください:")
        print("  --demo : クイックデモ実行")
        print("  --test : システムテスト実行")

if __name__ == "__main__":
    main()