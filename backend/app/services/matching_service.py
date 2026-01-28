from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from thefuzz import fuzz
import re
from app.models.inventory import AssetInventory
from app.services.ai_service import ai_service


class MatchingService:
    def __init__(self):
        self.min_fuzzy_score = 60  # Minimum fuzzy match score
        # Pattern to detect spec-like content in product name
        self.spec_pattern = re.compile(r'(\d+寸|\d+英寸|\d+口|\d+端口|\d+[TGMK]B?|\d+[MGK]|千兆|万兆|POE|poe)')
    
    def _needs_parsing(self, product_name: str) -> bool:
        """Check if product name contains spec-like content that needs AI parsing"""
        return bool(self.spec_pattern.search(product_name))
        
    def fuzzy_search(
        self, 
        db: Session, 
        product_name: str, 
        spec: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search inventory using fuzzy matching, including category_alias"""
        # First, try SQL LIKE query
        query = db.query(AssetInventory)
        
        # Build search conditions - include category_alias
        search_terms = product_name.split()
        conditions = []
        for term in search_terms:
            if len(term) >= 2:
                conditions.append(AssetInventory.product_name.like(f"%{term}%"))
                conditions.append(AssetInventory.category.like(f"%{term}%"))
                conditions.append(AssetInventory.category_alias.like(f"%{term}%"))
                conditions.append(AssetInventory.spec.like(f"%{term}%"))
        
        if conditions:
            candidates = query.filter(or_(*conditions)).limit(50).all()
        else:
            candidates = query.limit(50).all()
        
        # Score candidates using fuzzy matching
        scored_candidates = []
        for item in candidates:
            # Calculate name similarity
            name_score = fuzz.token_set_ratio(product_name, item.product_name or "")
            
            # Calculate category_alias similarity (for vague requirements like "综合布线")
            alias_score = 0
            if item.category_alias:
                alias_score = fuzz.token_set_ratio(product_name, item.category_alias)
            
            # Calculate spec similarity if provided
            spec_score = 0
            if spec and item.spec:
                spec_score = fuzz.token_set_ratio(spec, item.spec)
            
            # Combined score - prioritize alias match for vague requirements
            if alias_score > name_score:
                # If category_alias matches better, use it as primary score
                total_score = alias_score * 0.6 + name_score * 0.2 + spec_score * 0.2
            else:
                total_score = name_score * 0.7 + spec_score * 0.3 if spec else name_score
            
            if total_score >= self.min_fuzzy_score:
                scored_candidates.append({
                    "id": item.id,
                    "product_name": item.product_name,
                    "category": item.category,
                    "category_alias": item.category_alias,
                    "spec": item.spec,
                    "quantity": float(item.quantity) if item.quantity else None,
                    "unit": item.unit,
                    "sale_price": float(item.sale_price) if item.sale_price else None,
                    "supplier": item.supplier,
                    "fuzzy_score": total_score
                })
        
        # Sort by score and return top matches
        scored_candidates.sort(key=lambda x: x["fuzzy_score"], reverse=True)
        return scored_candidates[:limit]
    
    def search_by_category_alias(
        self,
        db: Session,
        alias: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search inventory by category_alias for vague requirements"""
        query = db.query(AssetInventory).filter(
            AssetInventory.category_alias.like(f"%{alias}%")
        ).limit(limit).all()
        
        return [{
            "id": item.id,
            "product_name": item.product_name,
            "category": item.category,
            "category_alias": item.category_alias,
            "spec": item.spec,
            "quantity": float(item.quantity) if item.quantity else None,
            "unit": item.unit,
            "sale_price": float(item.sale_price) if item.sale_price else None,
            "supplier": item.supplier,
        } for item in query]
    
    async def match_requirement(
        self,
        db: Session,
        req_name: str,
        req_spec: Optional[str] = None,
        req_quantity: Optional[float] = None
    ) -> Dict[str, Any]:
        """Match a single requirement with inventory"""
        parsed_name = req_name
        parsed_spec = ""
        
        # Step 0: Only use AI to parse if product name contains spec-like content
        if self._needs_parsing(req_name):
            try:
                parsed = await ai_service.parse_requirement(req_name)
                parsed_name = parsed.get("product_name", req_name)
                parsed_spec = parsed.get("spec", "")
            except Exception as e:
                # If AI parsing fails, use original name
                await ai_service._log("WARN", f"[匹配] 需求解析失败，使用原始值: {str(e)}")
        
        # Merge parsed spec with original spec
        if parsed_spec and req_spec:
            combined_spec = f"{parsed_spec} {req_spec}"
        elif parsed_spec:
            combined_spec = parsed_spec
        else:
            combined_spec = req_spec
        
        # Step 1: Fuzzy search for candidates (now includes category_alias)
        candidates = self.fuzzy_search(db, parsed_name, combined_spec)
        
        if not candidates:
            return {
                "matched_id": None,
                "matched_inventory": None,
                "confidence": 0,
                "reason": "未找到匹配的库存项",
                "parsed_name": parsed_name,
                "parsed_spec": parsed_spec
            }
        
        # Step 2: If high confidence match exists, return directly (skip AI)
        top_candidate = candidates[0]
        if top_candidate["fuzzy_score"] >= 85:
            reason = f"模糊匹配置信度: {top_candidate['fuzzy_score']:.0f}%"
            if top_candidate.get("category_alias"):
                reason += f" (分类: {top_candidate['category_alias']})"
            return {
                "matched_id": top_candidate["id"],
                "matched_inventory": top_candidate,
                "confidence": top_candidate["fuzzy_score"] / 100,
                "reason": reason,
                "parsed_name": parsed_name,
                "parsed_spec": parsed_spec
            }
        
        # Step 3: Use AI for better matching (only when fuzzy score < 85)
        try:
            ai_result = await ai_service.match_inventory(
                req_name, 
                req_spec,
                candidates[:5]  # Top 5 candidates for AI
            )
            
            matched_id = ai_result.get("matched_id")
            if matched_id:
                # Find the matched inventory
                matched_inv = next(
                    (c for c in candidates if c["id"] == matched_id), 
                    None
                )
                return {
                    "matched_id": matched_id,
                    "matched_inventory": matched_inv,
                    "confidence": ai_result.get("confidence", 0),
                    "reason": ai_result.get("reason", "AI匹配"),
                    "parsed_name": parsed_name,
                    "parsed_spec": parsed_spec
                }
            else:
                # Return top fuzzy match as fallback
                return {
                    "matched_id": top_candidate["id"],
                    "matched_inventory": top_candidate,
                    "confidence": top_candidate["fuzzy_score"] / 100 * 0.5,
                    "reason": f"AI未匹配，回退到模糊匹配: {top_candidate['product_name']}",
                    "parsed_name": parsed_name,
                    "parsed_spec": parsed_spec
                }
        except Exception as e:
            # Fallback to fuzzy match on AI error
            return {
                "matched_id": top_candidate["id"],
                "matched_inventory": top_candidate,
                "confidence": top_candidate["fuzzy_score"] / 100 * 0.5,
                "reason": f"AI服务异常，使用模糊匹配: {str(e)[:50]}",
                "parsed_name": parsed_name,
                "parsed_spec": parsed_spec
            }


matching_service = MatchingService()
