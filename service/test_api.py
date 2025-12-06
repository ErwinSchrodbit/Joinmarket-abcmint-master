# 测试脚本 - 验证混币服务API

import requests
import json
import time

# 服务地址
BASE_URL = "http://localhost:5000"

def test_create_job():
    """测试创建混币任务"""
    data = {
        "amount": 40.0,
        "targetAddress": "84LEUEGGvnZwnSSTpAfu7gS8b9Sey3yqTVyk69ppafLJkoqgA"
    }
    
    response = requests.post(f"{BASE_URL}/api/mix/request", json=data)
    print(f"创建任务响应: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"任务ID: {result['jobId']}")
        print(f"入金地址: {result['depositAddress']}")
        print(f"混币数量: {result['amount']}")
        return result['jobId']
    else:
        print(f"错误: {response.text}")
        return None

def test_get_status(job_id):
    """测试查询任务状态"""
    response = requests.get(f"{BASE_URL}/api/mix/status?jobId={job_id}")
    print(f"\n查询状态响应: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"状态: {result['status']}")
        print(f"确认数: {result['confirmations']}")
        if result['txid1']:
            print(f"第一步交易: {result['txid1']}")
        if result['txid2']:
            print(f"第二步交易: {result['txid2']}")
        if result['error']:
            print(f"错误: {result['error']}")
        return result
    else:
        print(f"错误: {response.text}")
        return None

def main():
    print("ABCMint 混币服务测试")
    print("=" * 50)
    
    # 测试创建任务
    job_id = test_create_job()
    if not job_id:
        print("创建任务失败")
        return
    
    print("\n任务已创建，请向显示的入金地址发送指定数量的 ABCMint")
    print("服务将自动检测入金并开始混币流程...")
    
    # 持续监控状态
    print("\n开始监控任务状态...")
    while True:
        status = test_get_status(job_id)
        if status:
            if status['status'] in ['completed', 'error']:
                if status['status'] == 'completed':
                    print("\n✅ 混币完成！")
                else:
                    print(f"\n❌ 混币失败: {status['error']}")
                break
        time.sleep(30)  # 每30秒检查一次

if __name__ == "__main__":
    main()