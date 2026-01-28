import httpx
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from app.core.config import settings


# Global log queue for SSE
log_queues: Dict[str, asyncio.Queue] = {}

# Global HTTP client for connection reuse
_http_client: Optional[httpx.AsyncClient] = None


def get_timestamp():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


async def get_http_client() -> httpx.AsyncClient:
    """Get or create a shared HTTP client with connection pooling"""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=30.0),
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    return _http_client


EXTRACT_PROMPT = """你是一个专业的采购需求分析专家。请从以下采购需求中提取结构化信息。

要求：
1. 识别每一项采购需求
2. 提取产品名称、规格型号、采购数量
3. 标准化产品名称（去除口语化表述）
4. 只返回JSON数组，不要有其他内容

输出格式示例：
[
  {{"name": "产品名称", "spec": "规格型号", "quantity": 1}}
]

采购需求内容：
{content}"""


PARSE_REQUIREMENT_PROMPT = """你是采购需求解析专家。请从以下需求描述中提取产品名称和规格信息。

需求描述：{requirement}

请识别并分离：
1. 产品名称：核心产品名（如"电子餐牌"、"显示器"、"交换机"等）
2. 规格描述：尺寸、型号、参数等信息（如"50寸"、"24口"、"1000M"等）

规则：
- 尺寸描述（如50寸、32英寸、21.5"）应归入规格
- 端口数量（如24口、48端口）应归入规格
- 速率/带宽（如千兆、1000M）应归入规格
- 容量（如500G、1TB）应归入规格
- 颜色、材质等特征也归入规格
- 如果没有明显的规格信息，spec返回空字符串

只返回JSON格式，不要有其他内容：
{{"product_name": "核心产品名", "spec": "规格信息"}}"""


MATCH_PROMPT = """你是采购匹配专家。请判断客户需求与候选库存项的匹配度。

客户需求：
- 产品名称：{req_name}
- 规格型号：{req_spec}

候选库存列表：
{candidates}

请选择最匹配的库存项，返回JSON格式（只返回JSON，不要有其他内容）：
{{"matched_id": 库存ID或null, "confidence": 0.0到1.0的置信度, "reason": "匹配原因"}}

如果没有匹配项，matched_id返回null，confidence返回0。"""


class AIService:
    def __init__(self):
        self.api_url = settings.DEEPSEEK_API_URL
        self.api_key = settings.DEEPSEEK_API_KEY
        self._log_callback: Optional[Callable] = None
        self._session_id: Optional[str] = None
    
    def set_session(self, session_id: str):
        """Set current session ID for logging"""
        self._session_id = session_id
        if session_id not in log_queues:
            log_queues[session_id] = asyncio.Queue()
    
    async def _log(self, level: str, message: str):
        """Log message to queue"""
        if self._session_id and self._session_id in log_queues:
            log_entry = {
                "time": get_timestamp(),
                "level": level,
                "message": message
            }
            await log_queues[self._session_id].put(log_entry)
        
    async def _call_api(self, prompt: str, purpose: str = "", max_retries: int = 3) -> str:
        """Call DeepSeek API with retry mechanism"""
        await self._log("INFO", f"[DeepSeek] 开始调用API - {purpose}")
        
        last_error = None
        
        for attempt in range(max_retries):
            if attempt > 0:
                wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
                await self._log("WARN", f"[DeepSeek] 第{attempt + 1}次重试，等待{wait_time}秒...")
                await asyncio.sleep(wait_time)
            
            start_time = datetime.now()
            
            try:
                client = await get_http_client()
                await self._log("INFO", f"[DeepSeek] 发送请求中...")
                response = await client.post(
                    f"{self.api_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.1,
                        "max_tokens": 4096
                    }
                )
                
                elapsed = (datetime.now() - start_time).total_seconds()
                await self._log("INFO", f"[DeepSeek] 响应状态码: {response.status_code}, 耗时: {elapsed:.2f}秒")
                
                response.raise_for_status()
                result = response.json()
                
                content = result["choices"][0]["message"]["content"]
                tokens_used = result.get("usage", {})
                await self._log("DEBUG", f"[DeepSeek] Token使用: 输入={tokens_used.get('prompt_tokens', 'N/A')}, 输出={tokens_used.get('completion_tokens', 'N/A')}")
                await self._log("INFO", f"[DeepSeek] API调用成功 - {purpose}")
                
                return content
                
            except httpx.TimeoutException as e:
                last_error = e
                await self._log("WARN", f"[DeepSeek] API调用超时 (尝试 {attempt + 1}/{max_retries})")
            except httpx.ConnectError as e:
                last_error = e
                await self._log("WARN", f"[DeepSeek] 网络连接失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
            except httpx.HTTPStatusError as e:
                last_error = e
                # Don't retry on 4xx errors (except 429 rate limit)
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    await self._log("ERROR", f"[DeepSeek] API错误: {e.response.status_code} - {e.response.text[:200]}")
                    raise
                await self._log("WARN", f"[DeepSeek] API错误 (尝试 {attempt + 1}/{max_retries}): {e.response.status_code}")
            except Exception as e:
                last_error = e
                await self._log("WARN", f"[DeepSeek] 调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
        
        # All retries failed
        await self._log("ERROR", f"[DeepSeek] API调用失败，已重试{max_retries}次 - {purpose}")
        raise last_error or Exception("API调用失败")
    
    async def extract_requirements(self, content: str) -> List[Dict[str, Any]]:
        """Extract structured requirements from text"""
        await self._log("INFO", "=== 开始解析采购需求 ===")
        await self._log("DEBUG", f"输入内容: {content[:100]}..." if len(content) > 100 else f"输入内容: {content}")
        
        prompt = EXTRACT_PROMPT.format(content=content)
        response = await self._call_api(prompt, "需求提取")
        
        await self._log("DEBUG", f"原始响应: {response[:200]}..." if len(response) > 200 else f"原始响应: {response}")
        
        # Parse JSON from response
        try:
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])
            
            items = json.loads(response)
            await self._log("INFO", f"成功解析 {len(items) if isinstance(items, list) else 0} 条需求")
            return items if isinstance(items, list) else []
        except json.JSONDecodeError as e:
            await self._log("WARN", f"JSON解析失败: {str(e)}, 尝试正则提取...")
            import re
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                try:
                    items = json.loads(match.group())
                    await self._log("INFO", f"正则提取成功, 共 {len(items)} 条需求")
                    return items
                except:
                    pass
            await self._log("ERROR", "需求解析失败")
            return []
    
    async def parse_requirement(self, requirement: str) -> Dict[str, str]:
        """Parse requirement to extract product name and spec using AI"""
        await self._log("INFO", f"[解析需求] 开始解析: {requirement}")
        
        prompt = PARSE_REQUIREMENT_PROMPT.format(requirement=requirement)
        
        try:
            response = await self._call_api(prompt, f"解析需求 '{requirement}'")
            response = response.strip()
            
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])
            
            result = json.loads(response)
            product_name = result.get("product_name", requirement)
            spec = result.get("spec", "")
            
            await self._log("INFO", f"[解析需求] 产品名称: {product_name}, 规格: {spec}")
            return {"product_name": product_name, "spec": spec}
            
        except Exception as e:
            await self._log("WARN", f"[解析需求] 解析失败: {str(e)}, 使用原始值")
            return {"product_name": requirement, "spec": ""}
    
    async def match_inventory(
        self, 
        req_name: str, 
        req_spec: Optional[str],
        candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Match requirement with inventory candidates using AI"""
        await self._log("INFO", f"--- 匹配需求: {req_name} ---")
        
        if not candidates:
            await self._log("WARN", "无候选库存项")
            return {"matched_id": None, "confidence": 0, "reason": "无候选库存"}
        
        await self._log("DEBUG", f"候选库存数量: {len(candidates)}")
        
        # Format candidates for prompt
        candidates_text = "\n".join([
            f"- ID: {c['id']}, 产品名称: {c['product_name']}, 规格: {c.get('spec', 'N/A')}, 分类: {c.get('category', 'N/A')}"
            for c in candidates
        ])
        
        prompt = MATCH_PROMPT.format(
            req_name=req_name,
            req_spec=req_spec or "未指定",
            candidates=candidates_text
        )
        
        response = await self._call_api(prompt, f"匹配 '{req_name}'")
        
        try:
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1])
            
            result = json.loads(response)
            await self._log("INFO", f"匹配结果: ID={result.get('matched_id')}, 置信度={result.get('confidence', 0):.0%}")
            return result
        except json.JSONDecodeError:
            await self._log("WARN", "匹配结果解析失败, 尝试正则提取...")
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                try:
                    result = json.loads(match.group())
                    await self._log("INFO", f"匹配结果: ID={result.get('matched_id')}, 置信度={result.get('confidence', 0):.0%}")
                    return result
                except:
                    pass
            await self._log("ERROR", "匹配解析失败")
            return {"matched_id": None, "confidence": 0, "reason": "解析失败"}


ai_service = AIService()
