import google.generativeai as genai
import os
from dotenv import load_dotenv

# 1. 強制讀取 .env
load_dotenv(override=True)
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ 錯誤：讀不到 API Key，請檢查 .env 檔案")
else:
    print(f"🔑 使用金鑰: {api_key[:10]}......")
    genai.configure(api_key=api_key)

    print("\n🔍 正在向 Google 查詢您的帳號可用模型...")
    try:
        # 列出所有支援 'generateContent' (聊天) 的模型
        count = 0
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"✅ 可用模型: {m.name}")
                count += 1
        
        if count == 0:
            print("⚠️ 帳號連接成功，但清單是空的！(可能需要去 GCP Console 啟用 Generative Language API)")
        else:
            print(f"\n🎉 恭喜！共找到 {count} 個可用模型。請選一個填回 ai_chat.py！")
            
    except Exception as e:
        print(f"❌ 連線失敗: {e}")