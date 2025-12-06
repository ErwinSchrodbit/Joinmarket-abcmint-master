#!/usr/bin/env python3
"""
ABCMint ミキシングサービス起動スクリプト

使用方法:
1. 環境変数の設定:
   $env:ABCMINT_RPC_HOST="127.0.0.1"
   $env:ABCMINT_RPC_PORT="8332"
   $env:ABCMINT_RPC_USER="youruser"
   $env:ABCMINT_RPC_PASSWORD="yourpass"

2. 依存関係のインストール:
   pip install -r service/requirements.txt

3. サービスの起動:
   python service/start_service.py

4. ブラウザでアクセス: http://localhost:5000
"""

import os
import sys
import subprocess

def main():
    # サービスディレクトリをPythonパスに追加
    service_dir = os.path.join(os.path.dirname(__file__), '..')
    if service_dir not in sys.path:
        sys.path.insert(0, service_dir)
    
    # 依存関係の確認
    try:
        import flask
        import qrcode
    except ImportError:
        print("依存パッケージをインストールしています...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'service/requirements.txt'])
        print("依存パッケージのインストールが完了しました")
    
    from service.app import app
    try:
        from waitress import serve
    except Exception:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'waitress'])
        from waitress import serve
    print("ABCMint ミキシングサービスを起動しています...")
    print("http://localhost:5000 にアクセスしてサービスを利用してください")
    serve(app, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    main()