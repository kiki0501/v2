import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from collections import defaultdict

class DailyStatsManager:
    """管理按天、按模型的统计数据"""
    
    def __init__(self, filepath="daily_stats.json"):
        self.filepath = filepath
        self.stats = {}  # {date: {model: {requests: 0, tokens: 0}}}
        self.lock = asyncio.Lock()
        self.load_stats()
    
    def get_beijing_date(self) -> str:
        """获取东八区当前日期 (YYYY-MM-DD)"""
        beijing_tz = timezone(timedelta(hours=8))
        now = datetime.now(beijing_tz)
        return now.strftime("%Y-%m-%d")
    
    def load_stats(self):
        """从文件加载统计数据"""
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.stats = json.load(f)
            print(f"📊 Loaded daily stats from {self.filepath}")
        except FileNotFoundError:
            self.stats = {}
            self.save_stats()
        except Exception as e:
            print(f"⚠️ Error loading daily stats: {e}")
            self.stats = {}
    
    def save_stats(self):
        """保存统计数据到文件"""
        try:
            with open(self.filepath, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Error saving daily stats: {e}")
    
    async def record_request(self, model: str, prompt_tokens: int = 0, completion_tokens: int = 0):
        """记录一次请求"""
        async with self.lock:
            date = self.get_beijing_date()
            
            # 初始化日期
            if date not in self.stats:
                self.stats[date] = {}
            
            # 初始化模型
            if model not in self.stats[date]:
                self.stats[date][model] = {
                    "requests": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0
                }
            
            # 更新统计
            self.stats[date][model]["requests"] += 1
            self.stats[date][model]["prompt_tokens"] += prompt_tokens
            self.stats[date][model]["completion_tokens"] += completion_tokens
            self.stats[date][model]["total_tokens"] += (prompt_tokens + completion_tokens)
            
            self.save_stats()
    
    def get_today_stats(self) -> Dict[str, Any]:
        """获取今天的统计数据"""
        date = self.get_beijing_date()
        return self.stats.get(date, {})
    
    def get_date_stats(self, date: str) -> Dict[str, Any]:
        """获取指定日期的统计数据"""
        return self.stats.get(date, {})
    
    def get_all_stats(self) -> Dict[str, Any]:
        """获取所有统计数据"""
        return self.stats
    
    def get_recent_days(self, days: int = 7) -> Dict[str, Any]:
        """获取最近N天的统计数据"""
        beijing_tz = timezone(timedelta(hours=8))
        today = datetime.now(beijing_tz).date()
        
        result = {}
        for i in range(days):
            date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
            if date in self.stats:
                result[date] = self.stats[date]
        
        return result
    
    def cleanup_old_data(self, keep_days: int = 30):
        """清理超过指定天数的旧数据"""
        beijing_tz = timezone(timedelta(hours=8))
        cutoff_date = (datetime.now(beijing_tz).date() - timedelta(days=keep_days)).strftime("%Y-%m-%d")
        
        dates_to_remove = [date for date in self.stats.keys() if date < cutoff_date]
        
        for date in dates_to_remove:
            del self.stats[date]
        
        if dates_to_remove:
            print(f"🧹 Cleaned up {len(dates_to_remove)} days of old data")
            self.save_stats()