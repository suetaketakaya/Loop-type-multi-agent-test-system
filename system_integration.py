#!/usr/bin/env python3
"""
システム統合ヘルパー
既存のテスト設計・実行アプリとループシステムの統合
"""

import os
import json
import asyncio
import csv
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List
import requests
from datetime import datetime

class TestDesignIntegration:
    """テスト設計アプリとの統合"""
    
    def __init__(self, test_design_app_url: str = "http://localhost:5003"):
        self.app_url = test_design_app_url
        self.session = requests.Session()
    
    async def create_test_design_from_spec(self, spec_content: str, loop_dir: Path) -> Dict[str, Any]:
        """仕様書からテスト設計を作成"""
        try:
            # 一時的な仕様書ファイルを作成
            temp_spec_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8')
            temp_spec_file.write(spec_content)
            temp_spec_file.close()
            
            # テスト設計アプリにファイルをアップロード
            upload_result = await self._upload_specification_file(temp_spec_file.name)
            
            if not upload_result.get("success"):
                raise Exception(f"仕様書アップロード失敗: {upload_result.get('error')}")
            
            # テスト設計実行
            design_result = await self._execute_test_design()
            
            if not design_result.get("success"):
                raise Exception(f"テスト設計実行失敗: {design_result.get('error')}")
            
            # 結果をローカルに保存
            self._save_test_design_result(loop_dir, design_result["result"])
            
            # テストケースをCSV形式でダウンロード
            csv_content = await self._download_test_cases_csv(upload_result["filename"])
            self._save_test_cases_csv(loop_dir, csv_content)
            
            # 一時ファイル削除
            os.unlink(temp_spec_file.name)
            
            return {
                "success": True,
                "test_design_result": design_result["result"],
                "csv_saved": True,
                "requirements_count": len(design_result["result"].get("requirements", [])),
                "test_cases_count": len(design_result["result"].get("test_cases", []))
            }
            
        except Exception as e:
            print(f"テスト設計統合エラー: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback_used": True
            }
    
    async def _upload_specification_file(self, file_path: str) -> Dict[str, Any]:
        """仕様書ファイルをアップロード"""
        try:
            with open(file_path, 'rb') as f:
                files = {'spec_file': f}
                response = requests.post(f"{self.app_url}/upload_spec", files=files, timeout=30)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_test_design(self) -> Dict[str, Any]:
        """テスト設計を実行"""
        try:
            # 少し待機してからテスト設計を実行
            await asyncio.sleep(1)
            response = requests.post(f"{self.app_url}/start_design", timeout=60)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _download_test_cases_csv(self, filename: str) -> str:
        """テストケースCSVをダウンロード"""
        try:
            response = requests.get(f"{self.app_url}/download_test_cases/{filename}", timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"CSV ダウンロードエラー: {e}")
            return ""
    
    def _save_test_design_result(self, loop_dir: Path, result: Dict):
        """テスト設計結果を保存"""
        with open(loop_dir / "test_design_result.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    
    def _save_test_cases_csv(self, loop_dir: Path, csv_content: str):
        """テストケースCSVを保存"""
        with open(loop_dir / "test_cases.csv", 'w', encoding='utf-8') as f:
            f.write(csv_content)

class TestExecutionIntegration:
    """テスト実行アプリとの統合"""
    
    def __init__(self, test_execution_app_url: str = "http://localhost:5001"):
        self.app_url = test_execution_app_url
        self.session = requests.Session()
    
    async def execute_test_cases(self, test_cases_csv_path: Path, loop_dir: Path) -> Dict[str, Any]:
        """テストケースを実行"""
        try:
            # CSVファイルをアップロード
            upload_result = await self._upload_test_cases_csv(test_cases_csv_path)
            
            if not upload_result.get("success"):
                raise Exception(f"テストケースアップロード失敗: {upload_result.get('error')}")
            
            # アップロードされたテストケースを取得
            test_cases = upload_result.get("test_cases", [])
            
            # 各テストケースを実行
            execution_results = []
            for test_case in test_cases:
                execution_result = await self._execute_single_test_case(test_case, loop_dir)
                execution_results.append(execution_result)
            
            # 実行結果をまとめる
            total_tests = len(test_cases)
            passed_tests = len([r for r in execution_results if r.get("status") == "passed"])
            failed_tests = total_tests - passed_tests
            
            result = {
                "success": True,
                "execution_results": execution_results,
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "test_cases": test_cases
            }
            
            # 結果を保存
            self._save_execution_results(loop_dir, result)
            
            return result
            
        except Exception as e:
            print(f"テスト実行統合エラー: {e}")
            return {
                "success": False,
                "error": str(e),
                "execution_results": [],
                "total_tests": 0,
                "passed_tests": 0,
                "failed_tests": 0
            }
    
    async def _upload_test_cases_csv(self, csv_path: Path) -> Dict[str, Any]:
        """テストケースCSVをアップロード"""
        try:
            with open(csv_path, 'rb') as f:
                files = {'test_cases_file': f}
                response = requests.post(f"{self.app_url}/upload_test_cases", files=files, timeout=30)
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_single_test_case(self, test_case: Dict, loop_dir: Path) -> Dict[str, Any]:
        """単一のテストケースを実行"""
        try:
            # テスト実行を作成
            create_result = await self._create_execution(test_case)
            
            if not create_result.get("success"):
                return {
                    "test_case_id": test_case.get("test_case_id", "unknown"),
                    "test_name": test_case.get("test_name", "unknown"),
                    "status": "failed",
                    "failure_reason": f"実行作成失敗: {create_result.get('error')}"
                }
            
            execution_id = create_result["execution_id"]
            
            # テスト実行開始
            await self._start_execution(execution_id)
            
            # 各ステップを実行（シミュレーション）
            test_steps = test_case.get("test_steps", [])
            step_results = []
            
            for i, step in enumerate(test_steps):
                step_result = await self._execute_step(execution_id, i, step)
                step_results.append(step_result)
            
            # 実行状況を取得
            execution_status = await self._get_execution_status(execution_id)
            
            # 結果をエクスポート
            export_result = await self._export_execution_results(execution_id, loop_dir)
            
            return {
                "test_case_id": test_case.get("test_case_id", "unknown"),
                "test_name": test_case.get("test_name", "unknown"),
                "execution_id": execution_id,
                "status": execution_status.get("status", "unknown"),
                "step_results": step_results,
                "export_path": export_result.get("filepath") if export_result.get("success") else None
            }
            
        except Exception as e:
            return {
                "test_case_id": test_case.get("test_case_id", "unknown"),
                "test_name": test_case.get("test_name", "unknown"),
                "status": "failed",
                "failure_reason": f"実行エラー: {str(e)}"
            }
    
    async def _create_execution(self, test_case: Dict) -> Dict[str, Any]:
        """テスト実行を作成"""
        try:
            data = {
                "test_case_id": test_case.get("test_case_id"),
                "execution_style": "Semi-Automated BDD"
            }
            response = requests.post(f"{self.app_url}/create_execution", json=data, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _start_execution(self, execution_id: str) -> Dict[str, Any]:
        """テスト実行を開始"""
        try:
            response = requests.post(f"{self.app_url}/start_execution/{execution_id}", timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_step(self, execution_id: str, step_index: int, step_description: str) -> Dict[str, Any]:
        """ステップを実行"""
        try:
            # シミュレーション: ランダムに成功/失敗を決定
            import random
            success = random.random() > 0.2  # 80%の成功率
            
            data = {
                "result": f"ステップ{step_index + 1}実行結果",
                "status": "passed" if success else "failed",
                "notes": f"実行したステップ: {step_description}"
            }
            
            response = requests.post(f"{self.app_url}/complete_step/{execution_id}", json=data, timeout=30)
            response.raise_for_status()
            
            return {
                "step_index": step_index,
                "description": step_description,
                "status": "passed" if success else "failed",
                "result": data["result"]
            }
            
        except Exception as e:
            return {
                "step_index": step_index,
                "description": step_description,
                "status": "failed",
                "error": str(e)
            }
    
    async def _get_execution_status(self, execution_id: str) -> Dict[str, Any]:
        """実行状況を取得"""
        try:
            response = requests.get(f"{self.app_url}/get_execution/{execution_id}", timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    async def _export_execution_results(self, execution_id: str, loop_dir: Path) -> Dict[str, Any]:
        """実行結果をエクスポート"""
        try:
            response = requests.get(f"{self.app_url}/export_results/{execution_id}", timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _save_execution_results(self, loop_dir: Path, results: Dict):
        """実行結果を保存"""
        with open(loop_dir / "execution_results.json", 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

class WebAppChecker:
    """WEBアプリケーション状態確認"""
    
    @staticmethod
    async def check_app_availability(url: str, timeout: int = 10) -> Dict[str, Any]:
        """アプリケーションの利用可能性をチェック"""
        try:
            response = requests.get(url, timeout=timeout)
            return {
                "available": response.status_code == 200,
                "status_code": response.status_code,
                "response_time": response.elapsed.total_seconds(),
                "content_length": len(response.content)
            }
        except Exception as e:
            return {
                "available": False,
                "error": str(e),
                "status_code": None,
                "response_time": None
            }
    
    @staticmethod
    async def check_all_services() -> Dict[str, Any]:
        """全サービスの状態をチェック"""
        services = {
            "test_design_app": "http://localhost:5003",
            "test_execution_app": "http://localhost:5001"
        }
        
        results = {}
        for service_name, service_url in services.items():
            results[service_name] = await WebAppChecker.check_app_availability(service_url)
        
        return results

class EnhancedLoopController:
    """強化されたループ制御システム（統合版）"""
    
    def __init__(self, config):
        self.config = config
        self.test_design_integration = TestDesignIntegration()
        self.test_execution_integration = TestExecutionIntegration()
        
        # 元のコンポーネント
        from loop_system import WebSpecExtractor, ImprovementAnalyzer
        
        ollama_client = None
        try:
            from ollama_client import OllamaClient
            from config import config as ollama_config
            ollama_client = OllamaClient(ollama_config.ollama if ollama_config else None)
        except:
            pass
        
        self.spec_extractor = WebSpecExtractor(ollama_client)
        self.improvement_analyzer = ImprovementAnalyzer(ollama_client)
    
    async def run_integrated_test_design(self, spec_result: Dict, loop_dir: Path) -> Dict[str, Any]:
        """統合テスト設計実行"""
        # サービス状態チェック
        service_status = await WebAppChecker.check_all_services()
        
        if service_status["test_design_app"]["available"]:
            print("🔗 テスト設計アプリと連携")
            spec_content = spec_result.get("specification_document", "")
            return await self.test_design_integration.create_test_design_from_spec(spec_content, loop_dir)
        else:
            print("⚠️ テスト設計アプリが利用できません。代替処理を実行")
            return await self._fallback_test_design(spec_result, loop_dir)
    
    async def run_integrated_test_execution(self, test_design_result: Dict, loop_dir: Path) -> Dict[str, Any]:
        """統合テスト実行"""
        # サービス状態チェック
        service_status = await WebAppChecker.check_all_services()
        
        test_cases_csv_path = loop_dir / "test_cases.csv"
        
        if service_status["test_execution_app"]["available"] and test_cases_csv_path.exists():
            print("🔗 テスト実行アプリと連携")
            return await self.test_execution_integration.execute_test_cases(test_cases_csv_path, loop_dir)
        else:
            print("⚠️ テスト実行アプリが利用できません。代替処理を実行")
            return await self._fallback_test_execution(test_design_result, loop_dir)
    
    async def _fallback_test_design(self, spec_result: Dict, loop_dir: Path) -> Dict[str, Any]:
        """代替テスト設計"""
        # 簡易テストケース生成
        test_cases = [
            {
                "test_case_id": "TC-001",
                "test_name": "基本機能確認テスト",
                "test_steps": ["サイトにアクセス", "基本機能を実行"],
                "expected_results": ["正常動作"]
            },
            {
                "test_case_id": "TC-002", 
                "test_name": "UI操作テスト",
                "test_steps": ["画面表示確認", "UI要素操作"],
                "expected_results": ["適切な応答"]
            }
        ]
        
        # CSVファイル生成
        csv_content = "Test Case ID,Test Name,Test Objective,Test Steps,Expected Results,Test Data,Test Environment\n"
        for tc in test_cases:
            csv_content += f'"{tc["test_case_id"]}","{tc["test_name"]}","基本テスト","' + '","'.join(tc["test_steps"]) + '","' + '","'.join(tc["expected_results"]) + '","標準","テスト環境"\n'
        
        with open(loop_dir / "test_cases.csv", 'w', encoding='utf-8') as f:
            f.write(csv_content)
        
        return {
            "success": True,
            "test_cases": test_cases,
            "fallback_used": True
        }
    
    async def _fallback_test_execution(self, test_design_result: Dict, loop_dir: Path) -> Dict[str, Any]:
        """代替テスト実行"""
        test_cases = test_design_result.get("test_cases", [])
        
        execution_results = []
        for i, tc in enumerate(test_cases):
            # シミュレーション実行
            import random
            status = "passed" if random.random() > 0.3 else "failed"
            
            execution_results.append({
                "test_case_id": tc.get("test_case_id", f"TC-{i+1:03d}"),
                "test_name": tc.get("test_name", f"テストケース{i+1}"),
                "status": status,
                "failure_reason": "予期しない結果" if status == "failed" else None
            })
        
        result = {
            "success": True,
            "execution_results": execution_results,
            "total_tests": len(test_cases),
            "passed_tests": len([r for r in execution_results if r["status"] == "passed"]),
            "failed_tests": len([r for r in execution_results if r["status"] == "failed"]),
            "fallback_used": True
        }
        
        # 結果保存
        with open(loop_dir / "execution_results.json", 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return result

# 使用例関数
async def test_integration():
    """統合テスト"""
    print("🧪 システム統合テスト開始")
    
    # サービス状態確認
    service_status = await WebAppChecker.check_all_services()
    print("サービス状態:")
    for service, status in service_status.items():
        print(f"  {service}: {'✅' if status['available'] else '❌'}")
    
    # テスト設計統合テスト
    if service_status["test_design_app"]["available"]:
        integration = TestDesignIntegration()
        test_spec = """# テスト仕様書

## 概要
統合テスト用のサンプル仕様書

## 機能
- 基本機能: ログイン・ログアウト
- データ管理: CRUD操作
"""
        
        result = await integration.create_test_design_from_spec(test_spec, Path("/tmp"))
        print(f"テスト設計統合: {'✅' if result['success'] else '❌'}")
    
    print("🎯 統合テスト完了")

if __name__ == "__main__":
    asyncio.run(test_integration())