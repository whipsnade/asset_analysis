from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from thefuzz import fuzz
from app.models.inventory import AssetInventory
from app.services.ai_service import ai_service


class MatchingService:
    def __init__(self):
        self.min_fuzzy_score = 60  # Minimum fuzzy match score
        
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
        # Step 1: Fuzzy search for candidates (now includes category_alias)
        candidates = self.fuzzy_search(db, req_name, req_spec)
        
        if not candidates:
            return {
                "matched_id": None,
                "matched_inventory": None,
                "confidence": 0,
                "reason": "未找到匹配的库存项"
            }
        
        # Step 2: If high confidence match exists, return directly
        top_candidate = candidates[0]
        if top_candidate["fuzzy_score"] >= 90:
            reason = f"模糊匹配置信度: {top_candidate['fuzzy_score']:.0f}%"
            if top_candidate.get("category_alias"):
                reason += f" (分类: {top_candidate['category_alias']})"
            return {
                "matched_id": top_candidate["id"],
                "matched_inventory": top_candidate,
                "confidence": top_candidate["fuzzy_score"] / 100,
                "reason": reason
            }
        
        # Step 3: Use AI for better matching
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
                    "reason": ai_result.get("reason", "AI匹配")
                }
            else:
                # Return top fuzzy match as fallback
                return {
                    "matched_id": top_candidate["id"],
                    "matched_inventory": top_candidate,
                    "confidence": top_candidate["fuzzy_score"] / 100 * 0.5,
                    "reason": f"AI未匹配，回退到模糊匹配: {top_candidate['product_name']}"
                }
        except Exception as e:
            # Fallback to fuzzy match on AI error
            return {
                "matched_id": top_candidate["id"],
                "matched_inventory": top_candidate,
                "confidence": top_candidate["fuzzy_score"] / 100 * 0.5,
                "reason": f"AI服务异常，使用模糊匹配: {str(e)}"
            }


matching_service = MatchingService()
