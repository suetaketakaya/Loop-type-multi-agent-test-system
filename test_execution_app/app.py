#!/usr/bin/env python3
"""
テスト実行アプリケーション
テストベーステスト実行と人間による介入をサポート
"""

import os
import json
import csv
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
import sys

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-execution-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# グローバル変数
test_executions = {}
current_execution = None
test_cases = []

class TestExecution:
    """テスト実行クラス"""
    
    def __init__(self, test_case_id: str, test_name: str, test_steps: List[str], expected_results: List[str]):
        self.test_case_id = test_case_id
        self.test_name = test_name
        self.test_steps = test_steps
        self.expected_results = expected_results
        self.status = "pending"  # pending, running, completed, failed, human_intervention
        self.current_step = 0
        self.results = []
        self.human_interventions = []
        self.start_time = None
        self.end_time = None
        self.execution_style = "manual"  # manual, automated, hybrid
    
    def start_execution(self):
        """テスト実行開始"""
        self.start_time = datetime.now()
        self.status = "running"
        self.current_step = 0
    
    def complete_step(self, step_result: Dict[str, Any]):
        """ステップ完了"""
        self.results.append(step_result)
        self.current_step += 1
        
        if self.current_step >= len(self.test_steps):
            self.status = "completed"
            self.end_time = datetime.now()
    
    def add_human_intervention(self, intervention_type: str, description: str, result: str):
        """人間による介入を記録"""
        intervention = {
            "type": intervention_type,
            "description": description,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        self.human_interventions.append(intervention)
    
    def to_dict(self):
        """辞書形式で返す"""
        return {
            "test_case_id": self.test_case_id,
            "test_name": self.test_name,
            "test_steps": self.test_steps,
            "expected_results": self.expected_results,
            "status": self.status,
            "current_step": self.current_step,
            "results": self.results,
            "human_interventions": self.human_interventions,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "execution_style": self.execution_style
        }

class TestExecutionManager:
    """テスト実行マネージャー"""
    
    def __init__(self):
        self.executions = {}
        self.execution_styles = {
            "Human-in-the-Loop Driven": "人間による確認・判断をシナリオに組み込む",
            "Manual Trigger Driven": "人間がトリガーを操作することが前提",
            "Observer Driven": "人間やセンサーが観察して結果を判断",
            "Semi-Automated BDD": "自動+手動のハイブリッド設計"
        }
    
    def create_execution(self, test_case: Dict[str, Any], execution_style: str = "Manual Trigger Driven") -> str:
        """テスト実行を作成"""
        execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{test_case['test_case_id']}"
        
        execution = TestExecution(
            test_case["test_case_id"],
            test_case["test_name"],
            test_case["test_steps"],
            test_case["expected_results"]
        )
        execution.execution_style = execution_style
        
        self.executions[execution_id] = execution
        return execution_id
    
    def get_execution(self, execution_id: str) -> TestExecution:
        """実行を取得"""
        return self.executions.get(execution_id)
    
    def start_execution(self, execution_id: str):
        """実行開始"""
        execution = self.get_execution(execution_id)
        if execution:
            execution.start_execution()
    
    def complete_step(self, execution_id: str, step_result: Dict[str, Any]):
        """ステップ完了"""
        execution = self.get_execution(execution_id)
        if execution:
            execution.complete_step(step_result)
    
    def add_human_intervention(self, execution_id: str, intervention_type: str, description: str, result: str):
        """人間による介入を追加"""
        execution = self.get_execution(execution_id)
        if execution:
            execution.add_human_intervention(intervention_type, description, result)
    
    def get_all_executions(self) -> List[Dict[str, Any]]:
        """全実行を取得"""
        return [{"id": k, **v.to_dict()} for k, v in self.executions.items()]
    
    def export_results(self, execution_id: str) -> str:
        """結果をCSV形式でエクスポート"""
        execution = self.get_execution(execution_id)
        if not execution:
            return None
        
        filename = f"test_execution_{execution_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = os.path.join("test_results", filename)
        os.makedirs("test_results", exist_ok=True)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                "Test Case ID", "Test Name", "Status", "Execution Style",
                "Start Time", "End Time", "Total Steps", "Completed Steps"
            ])
            writer.writerow([
                execution.test_case_id,
                execution.test_name,
                execution.status,
                execution.execution_style,
                execution.start_time.isoformat() if execution.start_time else "",
                execution.end_time.isoformat() if execution.end_time else "",
                len(execution.test_steps),
                execution.current_step
            ])
            
            # ステップ結果
            writer.writerow([])
            writer.writerow(["Step", "Result", "Status", "Timestamp"])
            for i, result in enumerate(execution.results):
                writer.writerow([
                    i + 1,
                    result.get("result", ""),
                    result.get("status", ""),
                    result.get("timestamp", "")
                ])
            
            # 人間による介入
            if execution.human_interventions:
                writer.writerow([])
                writer.writerow(["Human Interventions"])
                writer.writerow(["Type", "Description", "Result", "Timestamp"])
                for intervention in execution.human_interventions:
                    writer.writerow([
                        intervention["type"],
                        intervention["description"],
                        intervention["result"],
                        intervention["timestamp"]
                    ])
        
        return filepath

# グローバルマネージャー
execution_manager = TestExecutionManager()

@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html')

@app.route('/upload_test_cases', methods=['POST'])
def upload_test_cases():
    """テストケースファイルアップロード"""
    global test_cases
    
    if 'test_cases_file' not in request.files:
        return jsonify({"error": "ファイルが選択されていません"}), 400
    
    file = request.files['test_cases_file']
    if file.filename == '':
        return jsonify({"error": "ファイルが選択されていません"}), 400
    
    try:
        # CSVファイルを読み込み
        content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(content.splitlines())
        
        test_cases = []
        for row in csv_reader:
            test_case = {
                "test_case_id": row.get("Test Case ID", ""),
                "test_name": row.get("Test Name", ""),
                "test_objective": row.get("Test Objective", ""),
                "test_steps": [step.strip() for step in row.get("Test Steps", "").split(",") if step.strip()],
                "expected_results": [result.strip() for result in row.get("Expected Results", "").split(",") if result.strip()],
                "test_data": row.get("Test Data", ""),
                "test_environment": row.get("Test Environment", "")
            }
            test_cases.append(test_case)
        
        return jsonify({
            "success": True,
            "message": f"{len(test_cases)}個のテストケースが読み込まれました",
            "test_cases": test_cases
        })
        
    except Exception as e:
        return jsonify({"error": f"ファイル読み込みエラー: {str(e)}"}), 500

@app.route('/create_execution', methods=['POST'])
def create_execution():
    """テスト実行を作成"""
    data = request.get_json()
    test_case_id = data.get('test_case_id')
    execution_style = data.get('execution_style', 'Manual Trigger Driven')
    
    # テストケースを検索
    test_case = None
    for tc in test_cases:
        if tc['test_case_id'] == test_case_id:
            test_case = tc
            break
    
    if not test_case:
        return jsonify({"error": "テストケースが見つかりません"}), 404
    
    execution_id = execution_manager.create_execution(test_case, execution_style)
    
    return jsonify({
        "success": True,
        "execution_id": execution_id,
        "test_case": test_case
    })

@app.route('/start_execution/<execution_id>', methods=['POST'])
def start_execution(execution_id):
    """テスト実行開始"""
    execution_manager.start_execution(execution_id)
    
    return jsonify({
        "success": True,
        "message": "テスト実行を開始しました"
    })

@app.route('/complete_step/<execution_id>', methods=['POST'])
def complete_step(execution_id):
    """ステップ完了"""
    data = request.get_json()
    step_result = {
        "result": data.get('result', ''),
        "status": data.get('status', 'passed'),
        "timestamp": datetime.now().isoformat(),
        "notes": data.get('notes', '')
    }
    
    execution_manager.complete_step(execution_id, step_result)
    
    return jsonify({
        "success": True,
        "message": "ステップを完了しました"
    })

@app.route('/add_intervention/<execution_id>', methods=['POST'])
def add_intervention(execution_id):
    """人間による介入を追加"""
    data = request.get_json()
    
    execution_manager.add_human_intervention(
        execution_id,
        data.get('type', 'manual'),
        data.get('description', ''),
        data.get('result', '')
    )
    
    return jsonify({
        "success": True,
        "message": "介入を記録しました"
    })

@app.route('/get_execution/<execution_id>')
def get_execution(execution_id):
    """実行状況を取得"""
    execution = execution_manager.get_execution(execution_id)
    if not execution:
        return jsonify({"error": "実行が見つかりません"}), 404
    
    return jsonify(execution.to_dict())

@app.route('/get_all_executions')
def get_all_executions():
    """全実行を取得"""
    executions = execution_manager.get_all_executions()
    return jsonify(executions)

@app.route('/export_results/<execution_id>')
def export_results(execution_id):
    """結果をエクスポート"""
    filepath = execution_manager.export_results(execution_id)
    if not filepath:
        return jsonify({"error": "実行が見つかりません"}), 404
    
    return jsonify({
        "success": True,
        "filepath": filepath,
        "message": "結果をエクスポートしました"
    })

@app.route('/get_test_cases')
def get_test_cases():
    """テストケース一覧を取得"""
    return jsonify(test_cases)

@app.route('/get_execution_styles')
def get_execution_styles():
    """実行スタイル一覧を取得"""
    return jsonify(execution_manager.execution_styles)

if __name__ == '__main__':
    # テンプレートディレクトリを作成
    os.makedirs('test_execution_app/templates', exist_ok=True)
    os.makedirs('test_execution_app/static', exist_ok=True)
    os.makedirs('test_results', exist_ok=True)
    
    print("🚀 テスト実行アプリケーションを起動中...")
    print("📝 ポート: 5001")
    print("🌐 URL: http://localhost:5001")
    
    socketio.run(app, host='0.0.0.0', port=5001, debug=True, allow_unsafe_werkzeug=True) 