import pandas as pd
import numpy as np
from typing import List, Dict, Any, BinaryIO
from io import BytesIO


class ExcelService:
    def parse_inventory_excel(self, file: BinaryIO) -> List[Dict[str, Any]]:
        """Parse inventory Excel file"""
        df = pd.read_excel(file)
        
        # Map Chinese column names to English
        column_mapping = {
            '产品名称': 'product_name',
            '设备分类': 'category',
            '型号规格': 'spec',
            '数量': 'quantity',
            '单位': 'unit',
            '销售单价': 'sale_price',
            '销售总价': 'sale_total',
            '合同备注': 'contract_remark',
            '采购单价': 'purchase_price',
            '采购备注': 'purchase_remark',
            '供应商渠道': 'supplier'
        }
        
        # Rename columns
        df = df.rename(columns=column_mapping)
        
        # Replace NaN with None for proper JSON/SQL handling
        df = df.replace({np.nan: None})
        
        # Handle sale_total column (may contain comma-separated values)
        if 'sale_total' in df.columns:
            def parse_sale_total(x):
                if x is None or x == '':
                    return None
                try:
                    return float(str(x).replace(',', '').replace('，', ''))
                except:
                    return None
            df['sale_total'] = df['sale_total'].apply(parse_sale_total)
        
        # Convert to list of dicts
        records = df.to_dict('records')
        
        # Filter out empty rows
        records = [
            r for r in records 
            if r.get('product_name') and str(r['product_name']).strip()
        ]
        
        return records
    
    def parse_procurement_excel(self, file: BinaryIO) -> List[Dict[str, Any]]:
        """Parse procurement request Excel file"""
        df = pd.read_excel(file)
        
        # Try to identify columns
        records = []
        for _, row in df.iterrows():
            record = {}
            
            # Try to find product name
            for col in ['产品名称', '名称', '品名', '商品名称']:
                if col in df.columns and pd.notna(row.get(col)):
                    record['name'] = str(row[col])
                    break
            
            # Try to find spec/description
            for col in ['产品描述', '规格', '型号', '描述', '型号规格']:
                if col in df.columns and pd.notna(row.get(col)):
                    record['spec'] = str(row[col])
                    break
            
            # Try to find quantity
            for col in ['采购数量', '数量', '需求数量']:
                if col in df.columns and pd.notna(row.get(col)):
                    try:
                        record['quantity'] = float(row[col])
                    except:
                        record['quantity'] = None
                    break
            
            if record.get('name'):
                records.append(record)
        
        return records
    
    def generate_inventory_template(self) -> BytesIO:
        """Generate inventory Excel template"""
        columns = [
            '产品名称', '设备分类', '型号规格', '数量', '单位',
            '销售单价', '销售总价', '合同备注', '采购单价', '采购备注', '供应商渠道'
        ]
        df = pd.DataFrame(columns=columns)
        
        output = BytesIO()
        df.to_excel(output, index=False)
        output.seek(0)
        return output


excel_service = ExcelService()
