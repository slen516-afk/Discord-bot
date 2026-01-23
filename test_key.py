import os
import google.generativeai as genai
from dotenv import load_dotenv

# 1. 強制重新載入 .env
load_dotenv(override=True)

api_key = os.getenv("GEMINI_API_KEY")

print("-" * 30)
if not api_key:
    print("❌ 完蛋，讀不到 API Key！請檢查 .env 檔案")
else:
    # 顯示前 5 碼讓你確認是不是新的
    print(f"🔑 目前讀取到的 Key 前五碼: {api_key[:5]}...")
    print(f"🔑 (請確認這跟你在網頁上看到的新 Key 是否一樣？)")
    
    print("-" * 30)
    print("📡 正在測試這把 Key 能不能用...")
    
    genai.configure(api_key=api_key)
    try:
        # 測試最基本的 flash 模型
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content("Hi")
        print(f"✅ 成功！Key 是好的！回應: {response.text}")
    except Exception as e:
        print(f"❌ 失敗！這把 Key 還是壞的。\n錯誤訊息: {e}")