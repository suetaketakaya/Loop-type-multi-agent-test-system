#!/usr/bin/env python3
"""
テスト設計アプリケーション
マルチエージェントシステムを使用してテスト要求分析、テスト設計書、テスト項目書を作成
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, Any, List
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_socketio import SocketIO, emit
import sys

# 親ディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from multi_agent_system import MultiAgentSystem
from config import config, BOSS_CONFIG, WORKER_CONFIGS

app = Flask(__name__)
app.config['SECRET_KEY'] = 'test-design-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# グローバル変数
multi_agent_system = None
current_project = None
test_design_results = {}

class TestDesignAgent:
    """テスト設計専用エージェントクラス"""
    
    def __init__(self, name: str, role: str, model: str, ollama_client):
        self.name = name
        self.role = role
        self.model = model
        self.ollama_client = ollama_client
    
    async def analyze_requirements(self, spec_content: str) -> Dict[str, Any]:
        """機能仕様書からテスト要求を分析"""
        prompt = f"""
あなたは{self.role}です。以下の機能仕様書を分析して、テスト要求を抽出してください。

機能仕様書:
{spec_content}

以下の形式でJSONで回答してください:
{{
    "test_requirements": [
        {{
            "id": "REQ-001",
            "category": "機能テスト",
            "description": "テスト要求の説明",
            "priority": "高/中/低",
            "test_type": "単体/結合/システム/受入"
        }}
    ],
    "risk_areas": [
        {{
            "area": "リスク領域",
            "description": "リスクの説明",
            "mitigation": "対策"
        }}
    ]
}}
"""
        
        response = await self.ollama_client.generate(prompt, self.model)
        try:
            return json.loads(response)
        except:
            return {"test_requirements": [], "risk_areas": []}
    
    async def create_test_design(self, requirements: List[Dict], spec_content: str) -> Dict[str, Any]:
        """テスト設計書を作成"""
        prompt = f"""
あなたは{self.role}です。以下のテスト要求と機能仕様書からテスト設計書を作成してください。

機能仕様書:
{spec_content}

テスト要求:
{json.dumps(requirements, ensure_ascii=False, indent=2)}

以下の形式でJSONで回答してください:
{{
    "test_design": [
        {{
            "test_case_id": "TC-001",
            "requirement_id": "REQ-001",
            "test_name": "テストケース名",
            "test_objective": "テスト目的",
            "preconditions": ["前提条件"],
            "test_steps": ["ステップ1", "ステップ2"],
            "expected_results": ["期待結果"],
            "test_data": "テストデータ",
            "test_environment": "テスト環境"
        }}
    ]
}}
"""
        
        response = await self.ollama_client.generate(prompt, self.model)
        try:
            return json.loads(response)
        except:
            return {"test_design": []}

class TestDesignSystem:
    """テスト設計システム"""
    
    def __init__(self):
        from ollama_client import OllamaClient
        self.ollama_client = OllamaClient(config.ollama)
        self.agents = []
        
        # テスト設計専用エージェントを初期化
        agent_configs = [
            {"name": "Requirements_Analyst", "role": "要求分析エキスパート", "model": "llama3.2"},
            {"name": "Test_Designer", "role": "テスト設計エキスパート", "model": "llama3.2"},
            {"name": "Quality_Assurance", "role": "品質保証エキスパート", "model": "llama3.2"},
            {"name": "Risk_Analyst", "role": "リスク分析エキスパート", "model": "llama3.2"}
        ]
        
        for config in agent_configs:
            agent = TestDesignAgent(
                config["name"],
                config["role"],
                config["model"],
                self.ollama_client
            )
            self.agents.append(agent)
    
    async def create_test_design_document(self, spec_content: str) -> Dict[str, Any]:
        """テスト設計書を作成"""
        # Step 1: 要求分析
        requirements_results = []
        for agent in self.agents:
            if "Requirements" in agent.name or "Risk" in agent.name:
                result = await agent.analyze_requirements(spec_content)
                requirements_results.append(result)
        
        # 要求を統合
        all_requirements = []
        all_risks = []
        for result in requirements_results:
            all_requirements.extend(result.get("test_requirements", []))
            all_risks.extend(result.get("risk_areas", []))
        
        # Step 2: テスト設計
        design_results = []
        for agent in self.agents:
            if "Design" in agent.name or "Quality" in agent.name:
                result = await agent.create_test_design(all_requirements, spec_content)
                design_results.append(result)
        
        # 設計を統合
        all_test_cases = []
        for result in design_results:
            all_test_cases.extend(result.get("test_design", []))
        
        return {
            "requirements": all_requirements,
            "risks": all_risks,
            "test_cases": all_test_cases,
            "created_at": datetime.now().isoformat()
        }

# グローバルシステムインスタンス
test_design_system = None

@app.route('/')
def index():
    """メインページ"""
    return render_template('index.html')

@app.route('/upload_spec', methods=['POST'])
def upload_spec():
    """機能仕様書アップロード"""
    global current_project
    
    if 'spec_file' not in request.files:
        return jsonify({"error": "ファイルが選択されていません"}), 400
    
    file = request.files['spec_file']
    if file.filename == '':
        return jsonify({"error": "ファイルが選択されていません"}), 400
    
    # ファイルを保存
    filename = f"spec_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    filepath = os.path.join('inputreq', filename)
    os.makedirs('inputreq', exist_ok=True)
    file.save(filepath)
    
    current_project = {
        "filename": filename,
        "filepath": filepath,
        "uploaded_at": datetime.now().isoformat()
    }
    
    return jsonify({
        "success": True,
        "filename": filename,
        "message": "機能仕様書がアップロードされました"
    })

@app.route('/start_design', methods=['POST'])
async def start_design():
    """テスト設計開始"""
    global test_design_system, current_project
    
    if not current_project:
        return jsonify({"error": "機能仕様書がアップロードされていません"}), 400
    
    try:
        # 機能仕様書を読み込み
        with open(current_project["filepath"], 'r', encoding='utf-8') as f:
            spec_content = f.read()
        
        # テスト設計システムを初期化
        if not test_design_system:
            test_design_system = TestDesignSystem()
        
        # テスト設計実行
        result = await test_design_system.create_test_design_document(spec_content)
        
        # 結果を保存
        test_design_results[current_project["filename"]] = result
        
        return jsonify({
            "success": True,
            "result": result,
            "message": "テスト設計が完了しました"
        })
        
    except Exception as e:
        return jsonify({"error": f"テスト設計でエラーが発生しました: {str(e)}"}), 500

@app.route('/get_results/<filename>')
def get_results(filename):
    """結果を取得"""
    if filename in test_design_results:
        return jsonify(test_design_results[filename])
    else:
        return jsonify({"error": "結果が見つかりません"}), 404

@app.route('/download_test_cases/<filename>')
def download_test_cases(filename):
    """テストケースをCSV形式でダウンロード"""
    if filename not in test_design_results:
        return jsonify({"error": "結果が見つかりません"}), 404
    
    result = test_design_results[filename]
    test_cases = result.get("test_cases", [])
    
    # CSV形式で出力
    csv_content = "Test Case ID,Requirement ID,Test Name,Test Objective,Preconditions,Test Steps,Expected Results,Test Data,Test Environment\n"
    
    for tc in test_cases:
        csv_content += f'"{tc.get("test_case_id", "")}","{tc.get("requirement_id", "")}","{tc.get("test_name", "")}","{tc.get("test_objective", "")}","{",".join(tc.get("preconditions", []))}","{",".join(tc.get("test_steps", []))}","{",".join(tc.get("expected_results", []))}","{tc.get("test_data", "")}","{tc.get("test_environment", "")}"\n'
    
    return csv_content, 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': f'attachment; filename=test_cases_{filename}.csv'
    }

if __name__ == '__main__':
    # テンプレートディレクトリを作成
    os.makedirs('test_design_app/templates', exist_ok=True)
    os.makedirs('test_design_app/static', exist_ok=True)
    
    print("🚀 テスト設計アプリケーションを起動中...")
    print("📝 ポート: 5000")
    print("🌐 URL: http://localhost:5000")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True) 