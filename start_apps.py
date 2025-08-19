#!/usr/bin/env python3
"""
テストベーステストシステム起動スクリプト
2つのアプリケーションサーバーを同時に起動
"""

import os
import sys
import subprocess
import time
import signal
import threading
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def start_test_design_app():
    """テスト設計アプリケーションを起動"""
    print("🚀 テスト設計アプリケーションを起動中...")
    print("📝 ポート: 5003")
    print("🌐 URL: http://localhost:5003")
    
    os.chdir(os.path.join(BASE_DIR, "test_design_app"))
    subprocess.run([sys.executable, "app.py"])

def start_test_execution_app():
    """テスト実行アプリケーションを起動"""
    print("🚀 テスト実行アプリケーションを起動中...")
    print("📝 ポート: 5001")
    print("🌐 URL: http://localhost:5001")
    
    os.chdir(os.path.join(BASE_DIR, "test_execution_app"))
    subprocess.run([sys.executable, "app.py"])

def main():
    """メイン関数"""
    print("=" * 60)
    print("🔧 テストベーステストシステム")
    print("=" * 60)
    print()
    print("📋 システム概要:")
    print("• テスト設計アプリケーション (ポート5003)")
    print("• テスト実行アプリケーション (ポート5001)")
    print()
    print("🎯 機能:")
    print("• マルチエージェントによるテスト設計")
    print("• 人間による介入をサポートするテスト実行")
    print("• テストベース評価手法")
    print()
    
    # 必要なディレクトリを作成
    os.makedirs("inputreq", exist_ok=True)
    os.makedirs("test_results", exist_ok=True)
    
    # 両方のアプリケーションを並行して起動
    design_thread = threading.Thread(target=start_test_design_app)
    execution_thread = threading.Thread(target=start_test_execution_app)
    
    try:
        design_thread.start()
        time.sleep(2)  # 少し待機
        execution_thread.start()
        
        print("\n✅ 両方のアプリケーションが起動しました!")
        print("\n🌐 アクセスURL:")
        print("• テスト設計: http://localhost:5003")
        print("• テスト実行: http://localhost:5001")
        print("\n📝 使用方法:")
        print("1. テスト設計アプリで機能仕様書をアップロード")
        print("2. マルチエージェントがテストケースを生成")
        print("3. テスト実行アプリでテストケースをアップロード")
        print("4. 人間による介入を含むテスト実行")
        print("\n🛑 終了するには Ctrl+C を押してください")
        
        # メインスレッドを維持
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 アプリケーションを終了中...")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 